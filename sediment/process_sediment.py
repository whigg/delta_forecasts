import os
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import itertools
import pandas
import rasterio
import fiona
import pint
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from collections import OrderedDict
import networkx as nx

from util import in_new_process, getLogger


def rasterize_grand_dams(env, target, source):
    ureg = pint.UnitRegistry()
    Q_ = ureg.Quantity

    with rasterio.open(str(source[1]), 'r') as basins_rast:
        basins = basins_rast.read(1)
        meta = basins_rast.meta.copy()
    affine = meta['affine']
    resvol = np.zeros_like(basins)
    with fiona.open(str(source[0]), 'r') as dams:
        for dam in dams:
            props = dam['properties']
            if ((int(props['QUALITY'].split(':')[0]) <= 3) and #verified, good, or fair
                    (props['CAP_MCM'] > 0)):
                lon = props['LONG_DD']
                lat = props['LAT_DD']
                vol = Q_(1e6 * props['CAP_MCM'], 'm**3').to('km**3').magnitude
                x, y = map(np.floor, ~affine * (lon, lat))
                resvol[y, x] += vol

    with rasterio.open(str(target[0]), 'w', **meta) as resvol_rast:
        resvol_rast.write(resvol, 1)
    return 0


def compute_I(env, target, source):
    Ag = pandas.read_pickle(str(source[0]))
    I = (1 + 0.09*Ag)
    I.to_pickle(str(target[0]))
    return 0


def res_trapping_bulk(env, target, source):
    ureg = pint.UnitRegistry()
    Q_ = ureg.Quantity

    utilization = 0.67
    with rasterio.open(str(source[0]), 'r') as resrast,\
             rasterio.open(str(source[1]), 'r') as disrast,\
             rasterio.open(str(source[2]), 'r') as basinrast:
        kwargs = resrast.meta.copy()
        resvol = Q_(resrast.read(1, masked=True), 'km**3').to('m**3').magnitude * utilization
        dis = Q_(disrast.read(1, masked=True), 'm**3/s').to('m**3/year').magnitude
        basins = basinrast.read(1, masked=True)
    resvol.mask[resvol==0] = True
    basin_ids = pandas.read_pickle(str(source[3]))

    Te = []
    for delta, basin_id in basin_ids.index:
        pix = np.logical_and(basins == basin_id, resvol>0)
        res_time = resvol[pix].sum() / dis[basins==basin_id].max()
        Te.append(1 - (0.05/np.sqrt(res_time)))
    Te = [te if (te is not np.ma.masked and te >= 0) else 0 for te in Te]

    Te = pandas.Series(Te, index=basin_ids.index)
    Te.to_pickle(str(target[0]))
    return 0


def res_trapping_subbasins(env, target, source):
    ureg = pint.UnitRegistry()
    Q_ = ureg.Quantity

    with rasterio.open(str(source[0]), 'r') as rast:
        resvol = rast.read(1)
    with rasterio.open(str(source[1]), 'r') as rast:
        dis = rast.read(1)
    with rasterio.open(str(source[2]), 'r') as rast:
        basins = rast.read(1)
    networks = pandas.read_pickle(str(source[3]))

    logger = getLogger(target)

    utilization = 0.67
    resvol = utilization * Q_(resvol, 'km**3').to('m**3').magnitude
    resvol[resvol<0] = 0
    dis = Q_(dis, 'm**3/s').to('m**3/year').magnitude

    TE = pandas.Series(0.0, index=networks.index)
    for (delta, basinid), G in list(networks.iteritems()):
        logger.info('{0} - {1}'.format(delta, basinid))
        topo_sort = nx.topological_sort(G)
        for node in topo_sort:
            G.node[node]['resvol'] = resvol[node[1], node[0]]
            G.node[node]['resvol_agg'] = resvol[node[1], node[0]] + sum([G.node[n]['resvol_agg'] for n in G.predecessors(node)])

        mouth = topo_sort[-1]
        tes = []
        diss = []
        to_visit = [mouth]
        while to_visit:
            node = to_visit.pop(0)
            if resvol[node[1], node[0]] > 0:
                localdis = dis[node[1], node[0]]
                if localdis > 0:
                    dt = G.node[node]['resvol_agg'] / localdis
                    te = max(1 - (0.05 / np.sqrt(dt)), 0)
                    tes.append(te)
                    diss.append(localdis)
            else:
                to_visit.extend(G.predecessors(node))
        TE[(delta, basinid)] = sum([t*d for t,d in zip(tes, diss)]) / dis[basins==basinid].max()

    TE.to_pickle(str(target[0]))
    return 0


def parse_zarfl_xls(env, target, source):
    zarfl = pandas.read_excel(str(source[0]), sheetname='Table S7').iloc[:, 1:]
    deltas = pandas.read_pickle(str(source[1]))

    zarfl.columns = np.r_[zarfl.iloc[0,0], zarfl.iloc[1,1:]]
    zarfl = zarfl.set_index('Major river basin')
    zarfl = zarfl.iloc[2:, :]

    cols =  map(lambda s: s.replace(' ', '')
                          .replace(',', '')
                          .replace(u'\u2013', '-'),
                zarfl.columns)
    zarfl.columns = pandas.CategoricalIndex(cols, categories=cols, ordered=True)
    changename = {
            u'Hong (Red River)': 'Hong',
            u'Ganges-Brahmaputra': 'Ganges',
            u'Tigris \u2013 Euphrates': 'Shatt_el_Arab',
            }
    zarfl.rename(index=lambda d: changename.get(d, d), inplace=True)
    zarfl = zarfl.reindex(index=deltas.index).dropna(axis=0, how='all')

    def split_dam_counts(s):
        if '(' not in str(s):
            return [int(s), 0]
        else:
            return map(int, s.replace(')','').split('('))
    zarfl_new = zarfl.applymap(split_dam_counts).applymap(lambda t: t[0])
    zarfl_old = zarfl.applymap(split_dam_counts).applymap(lambda t: t[1])

    multicols = pandas.MultiIndex.from_product([zarfl.columns, ['new', 'old']], names=['Discharge class', 'Scenario'])
    zarfl = pandas.DataFrame(0, index=zarfl.index, columns=multicols)
    zarfl.loc[:, (slice(None), 'new')] = zarfl_new.values
    zarfl.loc[:, (slice(None), 'old')] = zarfl_old.values
    zarfl.to_pickle(str(target[0]))
    return 0


def add_new_reservoirs(env, target, source):
    '''
    Place new dams in along river network.  Finds location on river network
    with discharge closest to mean of the zarfl discharge class.  Dam location
    not considered, just underlying discharge - OK given calculation of res_trapping,
    which computes discharge-weighted average of reservoir trapping efficiency
    '''
    with rasterio.open(str(source[0])) as ressrc:
        res_meta = ressrc.meta
        res = ressrc.read(1)

    res_adj = pandas.read_pickle(str(source[1]))

    with rasterio.open(str(source[2])) as dissrc:
        dis = dissrc.read(1)

    with rasterio.open(str(source[3])) as basinsrc:
        basins = basinsrc.read(1)

    basinids = pandas.read_pickle(str(source[4]))

    def dis_class_endmembers(s):
        return map(float, s.replace('>','').split('-'))

    def dis_class_mean(s):
        return np.mean(dis_class_endmembers(s))

    # estimate typical dam sizes based on river discharge
    # assume new dams will be similar sizes with respect to riv dis as exisiting dams
    new_vols = pandas.Series(0.0, index=res_adj.columns.levels[res_adj.columns.names.index('Discharge class')])
    for dis_class in new_vols.index:
        endmembers = dis_class_endmembers(dis_class)
        if len(endmembers) == 2:
            dam_locs = np.logical_and(res>0, np.logical_and(dis>=endmembers[0], dis<endmembers[1]))
        elif len(endmembers) == 1:
            dam_locs = np.logical_and(res>0, dis>endmembers)
        else:
            raise ValueError
        new_vols[dis_class] = res[dam_locs].mean()

    for delta, deltabasins in basinids.groupby(level='Delta'):
        if delta not in res_adj.index:
            continue
        mask = np.ones_like(res)
        for _, basinid in deltabasins.index:
            mask = np.logical_and(mask, basins!=basinid)
        mask[res>0] = True   # mark existing reservoirs
        # loop over discharge classes in reverse order so biggest dams get placed first. not necessary unless very few valid locs
        for (dis_class, res_in_class) in reversed(list(res_adj.groupby(axis=1, level='Discharge class', sort=True))):
            num_new_res = res_in_class.loc[delta, (dis_class, 'new')]
            for i in range(num_new_res):
                valid_dis = np.ma.masked_where(mask, dis)
                new_loc = np.unravel_index(np.argmin(np.abs(valid_dis - dis_class_mean(dis_class))), dis.shape)
                res[new_loc] = new_vols.loc[dis_class]
                mask[new_loc] = True

    with rasterio.open(str(target[0]), 'w', **res_meta) as resout:
        resout.write(res, 1)
    return 0


def calc_new_res_volumes(env, source, target):
    '''
    Compute volumes of new reservoirs to be added to river network
    '''
    with rasterio.open(str(source[0])) as rast:
        res = rast.read(1)
    potential = pandas.read_pickle(str(source[1]))
    utilization = pandas.read_pickle(str(source[2]))
    with rasterio.open(str(source[3])) as rast:
        basins = rast.read(1)
    basinids = pandas.read_pickle(str(source[4]))
    method = env['method']

    new_res_vols = pandas.Series(None, index=basinids.index, dtype=object)

    if isinstance(method, int) or isinstance(method, float):
        factor = method
        mean_res = res[res>0].mean()
        for delta, basinid in basinids.index:
            res_vols = sorted(res[np.logical_and(basins==basinid, res>0)].tolist())
            if len(res_vols) == 0:
                new_res_vols[(delta, basinid)] = []
                continue
            new_vol = sum(res_vols) * (factor - 1.)
            new_res_vols[(delta, basinid)] = [mean_res] * int(new_vol // mean_res) + [new_vol % mean_res]
    else:
        ref_basin = method
        ref_basinid = basinids.loc[ref_basin].index.sort_values(ascending=True)[0]
        ref_util = utilization[ref_basin, ref_basinid]
        mean_res = res[res>0].mean()
        for delta, basinid in basinids.index:
            res_vols = sorted(res[np.logical_and(basins==basinid, res>0)].tolist())
            target_vol = ref_util * potential[delta, basinid]
            if target_vol < sum(res_vols):
                # handle seperately, don't add new res just shrink current ones
                new_res_vols[(delta, basinid)] = target_vol / sum(res_vols)
                continue
            new_vol = target_vol - sum(res_vols)
            new_res_vols[(delta, basinid)] = [mean_res] * int(new_vol // mean_res) + [new_vol % mean_res]

    new_res_vols.to_pickle(str(target[0]))
    return 0


def calc_new_res_volumes_zarfl(env, source, target):
    '''
    Compute volumes of new reservoirs to be added to river network, from zarfl data
    '''
    with rasterio.open(str(source[0])) as rast:
        res = rast.read(1)
    res_adj = pandas.read_pickle(str(source[1]))
    with rasterio.open(str(source[2])) as rast:
        dis = rast.read(1)
    with rasterio.open(str(source[3])) as rast:
        basins = rast.read(1)
    basinids = pandas.read_pickle(str(source[4]))

    new_res_vols = pandas.Series(None, index=basinids.index, dtype=object)

    def dis_class_endmembers(s):
        return map(float, s.replace('>','').split('-'))
    def dis_class_mean(s):
        return np.mean(dis_class_endmembers(s))

    # estimate typical dam sizes based on river discharge
    # assume new dams will be similar sizes with respect to riv dis as exisiting dams
    new_vols = pandas.Series(0.0, index=res_adj.columns.levels[res_adj.columns.names.index('Discharge class')])
    for dis_class in new_vols.index:
        endmembers = dis_class_endmembers(dis_class)
        if len(endmembers) == 2:
            dam_locs = np.logical_and(res>0, np.logical_and(dis>=endmembers[0], dis<endmembers[1]))
        elif len(endmembers) == 1:
            dam_locs = np.logical_and(res>0, dis>endmembers)
        else:
            raise ValueError
        new_vols[dis_class] = res[dam_locs].mean()
    for delta, nums_new in res_adj.loc[:, (slice(None), 'new')].iterrows():
        basinid = basinids.loc[delta].index.sort_values(ascending=True)[0]
        new_res_vols[(delta, basinid)] = []
        for (dis_size, _), num_new in nums_new.iteritems():
            for i in range(num_new):
                new_res_vols[(delta, basinid)].append(new_vols.loc[dis_size])

    new_res_vols.to_pickle(str(target[0]))
    return 0


@in_new_process
def add_new_reservoirs_on_network(env, source, target):
    with rasterio.open(str(source[0]), 'r') as rast:
        res_meta = rast.meta
        del res_meta['transform']
        res = rast.read(1)
    with rasterio.open(str(source[1]), 'r') as rast:
        potential = rast.read(1)
    with rasterio.open(str(source[2]), 'r') as rast:
        basins = rast.read(1)
    new_res_vols = pandas.read_pickle(str(source[3]))
    networks = pandas.read_pickle(str(source[4]))

    logger = getLogger(target)

    potential[potential<0] = 0

    agg_dist = 3

    def setup_potentials(G, Grev, topo_sorted, potential):
        for node in topo_sorted:
            upstream = nx.single_source_shortest_path(Grev, node, agg_dist).keys()
            G.node[node]['potential'] = potential[node[1], node[0]]
            G.node[node]['potential_remaining'] = potential[node[1], node[0]]
            G.node[node]['potential_agg'] = sum([G.node[n]['potential'] for n in upstream])
        return G

    def update_potentials(G, Grev, topo_sorted, potential, res, maxres):
        if maxres > 0:
            for node in topo_sorted:
                upstream = nx.single_source_shortest_path(Grev, node, agg_dist).keys()
                factor = 1. - res[node[1],node[0]] / maxres
                for n in upstream:
                    G.node[n]['potential_remaining'] = G.node[n]['potential'] * factor
        max_rem_agg = -1
        for node in topo_sorted:
            upstream = nx.single_source_shortest_path(Grev, node, agg_dist).keys()
            G.node[node]['potential_rem_agg'] = sum([G.node[n]['potential_remaining'] for n in upstream])
            if G.node[node]['potential_rem_agg'] > max_rem_agg:
                max_rem_agg = G.node[node]['potential_rem_agg']
                max_node = node
        return G, max_node

    for (delta, basinid), G in networks.iteritems():
        logger.info('{0} - {1}'.format(delta, basinid))
        if isinstance(new_res_vols[(delta, basinid)], float):
            if np.isfinite(new_res_vols[(delta, basinid)]):
                # simple scaling factor
                for node in G:
                    res[node[1], node[0]] *= new_res_vols[(delta, basinid)]
            # else nan, don't modify reservoirs for this basin
            continue

        Grev = G.reverse()
        topo_sorted = nx.topological_sort(G)

        maxres = res[basins==basinid].max()
        G = setup_potentials(G, Grev, topo_sorted, potential)
        G, max_node = update_potentials(G, Grev, topo_sorted, potential, res, maxres)
        for new_res in new_res_vols[(delta, basinid)]:
            res[max_node[1], max_node[0]] += new_res
            if res[max_node[1], max_node[0]] > maxres:
                maxres = res[max_node[1], max_node[0]]
            G, max_node = update_potentials(G, Grev, topo_sorted, potential, res, maxres)

    with rasterio.open(str(target[0]), 'w', **res_meta) as resout:
        resout.write(res, 1)
    return 0


def draw_res_network(G, potential, res):

    def draw(G, pos, field, vmin=None, vmax=None):
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        mpl.style.use('ggplot')
        fig, ax = plt.subplots(1, 1, figsize=(12,8))
        nx.draw_networkx(G, pos=pos, with_labels=False, node_size=80, node_color=field, cmap=mpl.cm.viridis, vmin=vmin, vmax=vmax, ax=ax)
        plt.ion()
        plt.show()

    def compute_potentials(G, potential, res):
        Grev = G.reverse()
        agg_dist = 3
        pos = {}
        maxres = np.max([res[n[1],n[0]] for n in G])
        for node in nx.topological_sort(G):
            upstream = nx.single_source_shortest_path(Grev, node, agg_dist).keys()
            G.node[node]['potential'] = potential[node[1], node[0]]
            G.node[node]['potential_remaining'] = potential[node[1], node[0]]
            if (maxres > 0) and (res[node[1], node[0]] > 0):
                factor = 1. - res[node[1],node[0]] / maxres
                for n in upstream:
                    G.node[n]['potential_remaining'] *= factor
        for node in nx.topological_sort(G):
            upstream = nx.single_source_shortest_path(Grev, node, agg_dist).keys()
            G.node[node]['potential_agg'] = sum([G.node[n]['potential'] for n in upstream])
            G.node[node]['potential_rem_agg'] = sum([G.node[n]['potential_remaining'] for n in upstream])
            pos[node] = (node[0], -node[1])
        return G, pos

    G, pos = compute_potentials(G, potential, res)
    nodes = G.nodes()
    draw(G, pos, [res[n[1],n[0]] for n in nodes])
    draw(G, pos, [G.node[n]['potential'] for n in nodes])
    draw(G, pos, [G.node[n]['potential_agg'] for n in nodes])
    draw(G, pos, [G.node[n]['potential_rem_agg'] for n in nodes])


def compute_res_potential_and_utilization(env, source, target):
    with rasterio.open(str(source[0]), 'r') as rast:
        basins = rast.read(1)
        meta = rast.meta
        meta['transform'] = meta['affine']
    with rasterio.open(str(source[1]), 'r') as rast:
        relief = rast.read(1)
    with rasterio.open(str(source[2]), 'r') as rast:
        runoff = rast.read(1)
    with rasterio.open(str(source[3]), 'r') as rast:
        res = rast.read(1)
    basinids = pandas.read_pickle(str(source[4]))

    invalid = np.logical_or(relief<0, runoff<0)
    relief[relief < 0] = 0
    runoff[runoff < 0] = 0
    potential = relief * runoff

    basin_potential = pandas.Series(index=basinids.index)
    basin_resvol = pandas.Series(index=basinids.index)
    for (delta, basinid) in basinids.index:
        basin_potential[(delta, basinid)] = potential[basins==basinid].sum()
        basin_resvol[(delta, basinid)] = res[basins==basinid].sum()
    utilization = basin_resvol / basin_potential
    utilization[utilization.isnull()] = 0

    basin_potential.to_pickle(str(target[0]))
    utilization.to_pickle(str(target[1]))

    potential[invalid] = meta['nodata']
    with rasterio.open(str(target[2]), 'w', **meta) as tif:
        tif.write(potential, 1)
    return 0


# def compute_basin_res_utilization(env, source, target):
    # with rasterio.open(str(source[0]), 'r') as rast:
        # res = rast.read(1)
    # with rasterio.open(str(source[1]), 'r') as rast:
        # basins = rast.read(1)
    # basinids = pandas.read_pickle(str(source[2]))
    # potential = pandas.read_pickle(str(source[3]))

    # basin_resvol = pandas.Series(index=basinids.index)
    # for (delta, basinid) in basinids.index:
        # basin_resvol[(delta, basinid)] = res[basins==basinid].sum()

    # utilization = basin_resvol / potential
    # utilization.to_pickle(str(target[0]))
    # return 0


def scale_reservoirs_by_utilization(env, source, target):
    with rasterio.open(str(source[0]), 'r') as rast:
        res = rast.read(1)
        meta = rast.meta
        meta['transform'] = meta['affine']
    with rasterio.open(str(source[1]), 'r') as rast:
        basins = rast.read(1)
    potential = pandas.read_pickle(str(source[2]))
    utilization = pandas.read_pickle(str(source[2]))
    ref_basin = env['ref_basin']
    ref_basinid = potential.loc[ref_basin].index.sort_values(ascending=True)[0]

    ref_utilization = utilization[(ref_basin, ref_basinid)]

    res_adj = np.zeros_like(res)
    for (delta, basinid) in potential.index:
        basin_utilization = utilization[(delta, basinid)]
        if basin_utilization > 0:
            scaling = ref_utilization / basin_utilization
            res_adj[basins==basinid] = res[basins==basinid] * scaling
        else:
            # no reservoirs in this basin. add a single one of necessary size to some point in basin
            # other points already zero
            y, x = zip(*np.where(basins==basinid))[0]
            res_adj[y, x] = ref_utilization * potential[(delta, basinid)]

    utilization.to_pickle(str(target[0]))
    with rasterio.open(str(target[1]), 'w', **meta) as fout:
        fout.write(res_adj, 1)
    return 0


def make_res_maps(env, source, target):
    potential = pandas.read_pickle(str(source[0]))
    utilization = pandas.read_pickle(str(source[1]))
    potential = potential.drop(['Congo', 'Tone'])
    utilization = utilization.drop(['Congo', 'Tone'])
    with rasterio.open(str(source[2]), 'r') as rast:
        pot_rast = rast.read(1, masked=True)
        pot_rast[pot_rast<np.percentile(pot_rast, 30)] = rast.meta['nodata']
    with rasterio.open(str(source[3]), 'r') as rast:
        basins = rast.read(1, masked=True)
        x1, y1, x2, y2 = rast.window_bounds(((0, rast.height), (0, rast.width)))
        extent = [x1, x2, y1, y2]

    pot_basin_rast = np.zeros_like(basins)
    util_basin_rast = np.zeros_like(basins)

    # potential = potential.groupby(level='Delta').transform(np.sum)
    for (delta, basinid) in potential.index:
        # if (basins==basinid).sum() > 20:
        pot_basin_rast[basins==basinid] = np.log10(potential[(delta, basinid)])
        util_basin_rast[basins==basinid] = np.log10(utilization[(delta, basinid)])
    pot_basin_rast[pot_basin_rast==0] = np.nan
    pot_basin_rast[~np.isfinite(pot_basin_rast)] = np.nan
    util_basin_rast[util_basin_rast==0] = np.nan
    util_basin_rast[~np.isfinite(util_basin_rast)] = np.nan

    pc = ccrs.PlateCarree()
    fig, (a1, a2) = plt.subplots(1, 2,
                            subplot_kw={'projection': pc},
                            figsize=(10,3))

    cm = mpl.cm.plasma

    # a0.coastlines(lw=.5)
    # a0.add_feature(cfeature.OCEAN, facecolor='0.8', edgecolor='0.8')
    # im = a0.imshow(np.log10(pot_rast), origin='upper', extent=extent, transform=pc, cmap=cm)
    # fig.colorbar(im, ax=a0)
    # a0.set_title('Hydropower Potential')

    # a1.coastlines(lw=.5)
    a1.add_feature(cfeature.OCEAN, facecolor='0.8', edgecolor='0.8')
    im = a1.imshow(pot_basin_rast, origin='upper', extent=extent, transform=pc, cmap=cm)
    # divider = make_axes_locatable(a1)
    # cax = divider.append_axes('right', size='5%', pad=0.05)
    fig.colorbar(im, ax=a1)
    a1.set_title('Basin Hydropower Potential')

    # a2.coastlines(lw=.5)
    a2.add_feature(cfeature.OCEAN, facecolor='0.8', edgecolor='0.8')
    im = a2.imshow(util_basin_rast, origin='upper', extent=extent, transform=pc, cmap=cm)
    # divider = make_axes_locatable(a2)
    # cax = divider.append_axes('right', size='5%', pad=0.05)
    fig.colorbar(im, ax=a2)
    a2.set_title('Contemporary Utilization')

    fig.tight_layout()
    fig.savefig(str(target[0]))
    return 0


def compute_Eh(env, target, source):
    gdp = pandas.read_pickle(str(source[0]))
    popdens = pandas.read_pickle(str(source[1]))
    Eh = pandas.Series(1.0, index=gdp.index)
    Eh[np.logical_and(gdp>15000, popdens>200)] = 0.3
    Eh[np.logical_and(gdp<15000, popdens>200)] = 2
    Eh.to_pickle(str(target[0]))
    return 0


def compute_B(env, target, source):
    I = pandas.read_pickle(str(source[0]))
    L = pandas.read_pickle(str(source[1]))
    Te = pandas.read_pickle(str(source[2]))
    Eh = pandas.read_pickle(str(source[3]))
    B = I * L * (1 - Te) * Eh
    B.to_pickle(str(target[0]))
    return 0


def compute_Qs(env, target, source):
    ureg = pint.UnitRegistry()
    Q_ = ureg.Quantity

    B = pandas.read_pickle(str(source[0]))
    Q = Q_(pandas.read_pickle(str(source[1])), 'm**3/s').to('km**3/year').magnitude
    A = pandas.read_pickle(str(source[2]))
    R = pandas.read_pickle(str(source[3]))
    T = pandas.read_pickle(str(source[4]))
    w = 0.02 # for Qs units of kg/s.  Use w=0.0006 for MT/yt

    T[T<2] = 2
    Qs = w * B * Q**0.31 * A**0.5 * R * T
    Qs.to_pickle(str(target[0]))
    return 0


def plot_delta_scalars(env, target, source):
    mpl.style.use('ggplot')
    scenarios = env.get('scenarios', None)
    if not isinstance(scenarios, list):
        scenarios = [scenarios]
    ylabel = env['ylabel']
    xlabel = env['xlabel']
    title = env['title']
    yscale = env.get('yscale', ('linear', {}))
    exp_num = env.get('exp_num', None) # for color cycle control
    nsources = env['nsources']
    ylims = env.get('ylims', None)
    annot = env.get('annot', False)
    npanels = env.get('npanels', 1)

    qs = OrderedDict()
    for i in range(nsources):
        qs[scenarios[i]] = pandas.read_pickle(str(source[i])).groupby(level='Delta').sum()
    df_all = pandas.DataFrame(qs, columns=qs.keys())
    df_all = df_all.sort_values(by=scenarios[0], ascending=False)
    df_all = df_all.drop(['Congo', 'Tone'])
    df_all.index = [d.replace('_',' ') if 'Shatt' not in d else d.replace('_','-') for d in df_all.index]

    f, axs = plt.subplots(npanels, 1, figsize=(16/npanels,8))
    f.subplots_adjust(left=.15)
    if npanels == 1:
        axs = [axs]
    n0, n1 = 0, int(np.ceil(df_all.shape[0]/float(npanels)))
    for axi, a in enumerate(axs):
        firstpanel = (axi == 0)
        lastpanel = (axi == (len(axs) - 1))

        df = df_all.iloc[n0:n1,:]
        n0, n1 = n1, n1 + n1 - n0

        a.set_yscale(yscale[0], **yscale[1])
        if exp_num is None:
            df.plot(kind='bar', width=.8, ax=a, legend=firstpanel)
        else:
            color = next(itertools.islice(iter(mpl.rcParams['axes.prop_cycle']), exp_num, exp_num+1))['color']
            df.plot(kind='bar', width=.8, ax=a, color=color, legend=firstpanel)

        if annot:
            for p, yval in zip(a.patches, df.values.flatten('F')): # flatten in Fortran order to patch patches list, which goes over each data series first
                a.annotate(s='{:0.1f}'.format(yval),
                           xy=(p.get_x(), p.get_height()),
                           xytext=(p.get_x()+p.get_width()/2., p.get_height()),
                           textcoords='data',
                           ha='center', va='bottom',
                           fontsize=10,
                           )
        if ylims is not None:
            a.set_ylim(*ylims)

        if (npanels == 1):
            a.set_ylabel(ylabel)
        if lastpanel:
            a.set_xlabel(xlabel)
        # a.set_title(title)
    if (npanels > 1):
        f.text(0, .5, ylabel, ha='left', va='center', rotation='vertical', fontsize=mpl.rcParams['axes.labelsize'], color=mpl.rcParams['axes.labelcolor'])
    plt.tight_layout(rect=(.01,0,1,1))
    f.savefig(str(target[0]))
    plt.close(f)
    return 0


def plot_delta_scalars_lit(env, target, source):
    mpl.style.use('ggplot')
    scenarios = env.get('scenarios', None)
    if not isinstance(scenarios, list):
        scenarios = [scenarios]
    ylabel = env['ylabel']
    xlabel = env['xlabel']
    title = env['title']
    yscale = env.get('yscale', ('linear', {}))
    exp_num = env.get('exp_num', None) # for color cycle control
    nsources = env['nsources']
    ylims = env.get('ylims', None)
    annot = env.get('annot', False)
    npanels = env.get('npanels', 1)

    lit_vals = pandas.read_pickle(str(source[nsources-1]))
    qs = OrderedDict()
    for i in range(nsources-1):
        qs[scenarios[i]] = pandas.read_pickle(str(source[i])).groupby(level='Delta').sum()
    df_all = pandas.DataFrame(qs, columns=qs.keys())
    df_all = df_all.sort_values(by=scenarios[0], ascending=False)
    df_all = df_all.drop(['Congo', 'Tone'])
    df_all.index = [d.replace('_',' ') if 'Shatt' not in d else d.replace('_','-') for d in df_all.index]

    f, axs = plt.subplots(npanels, 1, figsize=(16/npanels,8))
    f.subplots_adjust(left=.15)
    if npanels == 1:
        axs = [axs]
    n0, n1 = 0, int(np.ceil(df_all.shape[0]/float(npanels)))

    for axi, a in enumerate(axs):
        firstpanel = (axi == 0)
        lastpanel = (axi == (len(axs) - 1))

        df = df_all.iloc[n0:n1,:]
        n0, n1 = n1, n1 + n1 - n0

        a.set_yscale(yscale[0], **yscale[1])
        if exp_num is None:
            df.plot(kind='bar', ax=a, legend=False)
        else:
            color = next(itertools.islice(iter(mpl.rcParams['axes.prop_cycle']), exp_num, exp_num+1))['color']
            df.plot(kind='bar', ax=a, color=color, legend=False)

        if ylims is None:
            ylims = a.get_ylim()

        if nsources > 2:
            barwidths = a.patches[0].get_width() * (nsources - 1)
            xs = pandas.Series([p.get_x() + barwidths/2. for p in a.patches[:df.shape[0]]], index=df.index)
        else:
            xs = pandas.Series([p.get_x()+p.get_width()/2. for p in a.patches], index=df.index)
        lit_vals['x'] = xs
        lit_vals['err'] = lit_vals['max'] - lit_vals['mean']
        a.errorbar(lit_vals['x'], lit_vals['mean'], yerr=lit_vals['err'], ecolor='k', lw=1, capsize=3, capthick=3, fmt='none', alpha=.7)

        if annot:
            for p, yval in zip(a.patches, df.values.flatten('F')): # flatten in Fortran order to patch patches list, which goes over each data series first
                a.annotate(s='{:0.1f}'.format(yval),
                           xy=(p.get_x(), p.get_height()),
                           xytext=(p.get_x()+p.get_width()/2., p.get_height()),
                           textcoords='data',
                           ha='center', va='bottom',
                           fontsize='small',
                           )

        a.set_ylim(*ylims)
        for delta, lit_val in lit_vals.iterrows():
            if lit_val['max'] > ylims[1]:
                a.annotate(s='({:0.0f})'.format(lit_val['max']),
                           xy=(lit_val['x'], ylims[1]),
                           xytext=(3, 3),
                           textcoords='offset points',
                           ha='left', va='bottom',
                           fontsize='small',
                           )
                # annotate to cover line with arrow
                a.annotate(s='',
                           xy=(lit_val['x'], ylims[1]),
                           xytext=(lit_val['x'], lit_val['min']),
                           xycoords='data',
                           textcoords='data',
                           arrowprops=dict(
                               arrowstyle='->',
                               color='k',
                               ),
                           zorder=0,
                           )

        if lastpanel:
            patches, labels = a.get_legend_handles_labels()
            patches = patches[:-1] # remove errorbars from legend
            labels = labels[:-1]
            a.legend(patches, labels, loc='best', framealpha=0)

        if (npanels == 1):
            a.set_ylabel(ylabel)
        if lastpanel:
            a.set_xlabel(xlabel)
        # a.set_title(title)
    if (npanels > 1):
        f.text(.01, .5, ylabel, ha='left', va='center', rotation='vertical', fontsize=mpl.rcParams['axes.labelsize'], color=mpl.rcParams['axes.labelcolor'])
    plt.tight_layout(rect=(.025,0,1,1))
    f.savefig(str(target[0]))
    plt.close(f)
    return 0


def plot_scalars_percent_change(env, target, source):
    mpl.style.use('ggplot')
    scenarios = env['scenarios']
    ylabel = env['ylabel']
    xlabel = env['xlabel']
    title = env['title']

    qs0 = pandas.read_pickle(str(source[0])).groupby(level='Delta').sum()
    qs1 = pandas.read_pickle(str(source[1])).groupby(level='Delta').sum()

    change = (qs1-qs0)/qs0 * 100.
    change = change.drop(['Congo', 'Tone'])
    if change.mean() > 0:
        ascending = False
    else:
        ascending = True
    change = change.sort_values(ascending=ascending)
    f, a = plt.subplots(1, 1, figsize=(16,8))
    change.plot(kind='bar', ax=a)
    a.set_ylabel(ylabel)
    a.set_xlabel(xlabel)
    # a.set_title(title + ', {} to {}'.format(scenarios[0], scenarios[1]))
    plt.tight_layout()
    f.savefig(str(target[0]))
    plt.close(f)

    return 0


def plot_rslr_timeseries(env, source, target):
    mpl.style.use('ggplot')
    ureg = pint.UnitRegistry()
    Q_ = ureg.Quantity

    scenarios = env['scenarios']
    deltas = env['deltas']
    slr_cur = env['slr_cur'] # 'mm/year'
    slr_2100_RCP2p6 = env['slr_2100_RCP2p6'] # 'mm/year'
    slr_2100_RCP8p5 = env['slr_2100_RCP8p5'] # 'mm/year'

    years = env['years']
    years = pandas.Series(range(years[0], years[1]+1))
    yr_index = pandas.Series(years.index) # 'year'

    rslr_land_A = pandas.read_pickle(str(source[0])) # 'mm/year'
    rslr_land_B = pandas.read_pickle(str(source[1])) # 'mm/year'

    slr_const = pandas.Series(slr_cur, index=yr_index) # 'mm/year'
    sl_const = (slr_const.cumsum() - slr_const[0]) / 1000. # 'm'

    slr_2p6 = pandas.Series(np.linspace(slr_cur, slr_2100_RCP2p6, len(yr_index)), index=yr_index) # 'mm/year'
    sl_2p6 = (slr_2p6.cumsum() - slr_2p6[0]) / 1000. # 'm'

    slr_8p5 = pandas.Series(np.linspace(slr_cur, slr_2100_RCP8p5, len(yr_index)), index=yr_index) # 'mm/year'
    sl_8p5 = (slr_8p5.cumsum() - slr_8p5[0]) / 1000. # 'm'

    if len(deltas) == 3:
        fig, axs = plt.subplots(len(deltas), 1, figsize=(4, 3*len(deltas)))
        doxlabel = [2]
        doylabel = [0, 1, 2]
    elif len(deltas) == 6:
        fig, axarr = plt.subplots(3, 2, figsize=(4*2, 3*3))
        axs = axarr.flatten()
        doxlabel = [4, 5]
        doylabel = [0, 2, 4]
    else:
        raise NotImplementedError
    mpl.rcParams.update({
                         'axes.labelsize': 'small',
                         'axes.titlesize': 'medium',
                         'legend.fontsize': 'small'})
    linestyle = {'const': '-', '2p6': '--', '8p5': ':'}
    if not isinstance(axs, np.ndarray):
        axs = [axs]
    for i, (delta, ax) in enumerate(zip(deltas, axs)):
        for j, (rslr, c) in enumerate(zip([rslr_land_A, rslr_land_B], mpl.rcParams['axes.prop_cycle'])):
            rslr_const = (yr_index * (rslr[delta] + slr_cur)) / 1000. # 'm'
            rslr_2p6 = ((yr_index * rslr[delta]) / 1000.) + sl_2p6 # 'm'
            rslr_8p5 = ((yr_index * rslr[delta]) / 1000.) + sl_8p5 # 'm'
            rslr_const.index = years
            rslr_2p6.index = years
            rslr_8p5.index = years

            ax.plot(rslr_const, color=c['color'], lw=2, linestyle=linestyle['const'], label=scenarios[j])
            ax.plot(rslr_const, color=c['color'], lw=2, linestyle=linestyle['const'])
            ax.plot(rslr_2p6, color=c['color'], lw=2, linestyle=linestyle['2p6'])
            ax.plot(rslr_8p5, color=c['color'], lw=2, linestyle=linestyle['8p5'])


            # print delta, j, rslr_const[2100], rslr_2p6[2100], rslr_8p5[2100]

        ax.plot([], [], color='.5', lw=2, linestyle=linestyle['const'], label='Const SLR')
        ax.plot([], [], color='.5', lw=2, linestyle=linestyle['2p6'], label='RCP 2.6 SLR')
        ax.plot([], [], color='.5', lw=2, linestyle=linestyle['8p5'], label='RCP 8.5 SLR')
        ax.set_title(delta)
        if i == 0:
            ax.legend(loc=2, frameon=False, handlelength=3)
        if i in doxlabel:
            ax.set_xlabel('Year', fontsize='small')
        else:
            ax.xaxis.set_ticklabels([])
        if i in doylabel:
            ax.set_ylabel('Relative sea level rise, m', fontsize='small')
        ax.tick_params(axis='both', which='major', labelsize='small')

    fig.tight_layout()
    fig.savefig(str(target[0]))
    return 0
