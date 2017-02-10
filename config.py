import csv
from collections import OrderedDict


def clean_delta_name(delta):
    return delta.replace(' ','_').replace('-','_')

with open('deltaIDs.csv', 'r') as deltaIDs:
    next(deltaIDs)
    next(deltaIDs)
    deltas = {}
    reader = csv.DictReader(deltaIDs)
    for d in reader:
        deltas[clean_delta_name(d['Delta'])] = int(d['deltaID'])
# deltas = { # for testing
        # 'Chao_Phraya': 5,
        # 'Irrawaddy': 18,
        # 'Mekong': 26,
        # 'Mississippi': 27,
        # 'Nile': 30,
        # 'Yangtze': 46,
         # }
deltas = OrderedDict(sorted(deltas.items(), key=lambda t: t[0]))

common = {'deltas': deltas,
          'popyear': 2015,  # GPWv4 adjusted to UN 2015 numbers
          'elevyear': 2000, # SRTM year
          'rslryear': 2000,  # nominal based on various input data
          'un_pop_forecasts': range(2020, 2100+1, 10),
          'un_pop_names': ['Low', 'Medium', 'High'],
          'ssps': [1,2,3],
          'ssp_forecasts': range(1980, 2100+1, 10),
          'ssp_names': ['SSP1', 'SSP2', 'SSP3'],
          }

# EXPERIMENT configs
defaults = {
        'config_out': '#data/experiments/{exp}/config_{exp}.json',
        'deltas_source': ('tessler2015',
            '/Users/ztessler/data/deltas/maps/global_map_shp/global_map.shp'),
        'deltas': '#data/deltas.json',
        'delta_areas': '#data/delta_areas.pd',
        'delta_countries': '#data/delta_countries.json',

        'pop_dens_source': ('gpwv4',
            '/Users/ztessler/data/GPWv4_beta/gpw-v4-population-density-adjusted-to-2015-unwpp-country-totals-{popyear}/gpw-v4-population-density-adjusted-to-2015-unwpp-country-totals_{popyear}.tif'),
        'pop_dens_rast': '#data/experiments/{exp}/pop_dens_{popyear}{ver}.{ext}',
        'delta_pop_dens': '#data/experiments/{exp}/delta_pop_dens_{popyear}.pd',

        'delta_map': '#data/{delta}.json',
        'delta_pop_rast':
            '#data/gpwv4/{delta}_pop_{popyear}.tif',
        'delta_srtm_rast':
            '#data/srtm{srtm}/{delta}_srtm.tif',
        'delta_srtm_full_rast':
            '#data/srtm{srtm}/{delta}_srtm_full.tif',
        'delta_pop_hypso':
            '#data/experiments/{exp}/{delta}/{delta}_pop_elevations.pd',
        'pop_hypso':
            '#data/experiments/{exp}/pop_elevations.pd',
        'pop_hypso_growth': # populations at different elevations given rslr forecasts
            '#data/experiments/{exp}/pop_elevations_forecasts.pd',
        'ssp_pop_hypso_growth': '#data/experiments/{exp}/ssp_pop_elevations.pd',
        'pop_hypso_growth_rslr':
            '#data/experiments/{exp}/pop_elevations_forecasts_rslr.pd',
        'ssp_pop_hypso_growth_rslr': '#data/experiments/{exp}/ssp_pop_elevations_rslr.pd',
        'hypso_plot':
            '#figures/{exp}/hyspometric/{delta}_hypsometric_{popyear}.png',

        'basins_source': ('rgis',),
        'basins_rast': '#data/rgis/basins{ver}.{ext}',
        'basins30_source': ('rgis',),
        'basins30_rast': '#data/rgis/basins30{ver}.{ext}',
        'reservoir_source': ('grand', '/Users/ztessler/data/Dams_GRanD/dams-rev01-global-shp/GRanD_dams_v1_1.shp'),
        'reservoir_rast': '#data/experiments/{exp}/reservoirs{ver}.{ext}',
        'reservoir_adj': '#data/experiments/{exp}/reservoir_adj{ver}.{ext}',
        'discharge_source': ('rgis',),
        'discharge_rast': '#data/rgis/discharge{ver}.{ext}',
        'runoff_source': ('rgis',),
        'runoff_rast': '#data/rgis/runoff{ver}.{ext}',
        'airtemp_source': ('rgis',),
        'airtemp_rast': '#data/rgis/airtemp{ver}.{ext}',
        'ice_source': ('rgis',),
        'ice_rast': '#data/rgis/ice{ver}.{ext}',
        'lithology_source': ('rgis',),
        'lithology_rast': '#data/rgis/lithology{ver}.{ext}',
        'relief_source': ('rgis',),
        'relief_rast': '#data/rgis/relief{ver}.{ext}',

        'basin_res_potential': '#data/experiments/{exp}/res_potential.pd',

        'zeros_rast': '#data/zeros.tif',
        'zeros30_rast': '#data/zeros30.tif',
        'ones_rast': '#data/ones.tif',
        'ones30_rast': '#data/ones30.tif',

        'rslr_lit_source': ('higgins2014', '/Users/ztessler/data/RSLR/higgins_rslr.csv'),
        # 'rslr_lit_source': ('higgins2014_agg', '/Users/ztessler/data/RSLR/higgins_rslr_summary.csv'),
        'rslr_lit_mean_weight': 2,
        # 'rslr_lit_source': ('syvitski2009', '/Users/ztessler/data/RSLR/syvitski_2009_rslr.csv'),
        'rslr_lit': '#data/experiments/{exp}/rslr_lit.pd',

        'gia_source': ('grace', '/Users/ztessler/data/GIA/GIA.COMPRESSIBLE.GRIDS.nc'),
        'gia_model': 'GIA_n60_uplift_200km',
        'gia_uplift': '#data/experiments/{exp}/gia_uplift.{ext}',

        'sed_morph_source': ('syvitski_saito_2007', '/Users/ztessler/data/RSLR/syvitski_saito_2007_morph.csv'),
        'sed_retention': '#data/experiments/{exp}/sed_retention.pd',
        'accomodation_space': '#data/experiments/{exp}/accomodation_space.pd',
        'shape_factor': .5,

        'groundwater_source': ('wada', '/Users/ztessler/data/Groundwater_Wada2012/gwd02000.asc'),
        'groundwater_rast': '#data/experiments/{exp}/groundwater{ver}.{ext}',
        'oilgas_source': ('usgs',
            '/Users/ztessler/data/WorldPetroleumAssessment/tps_sumg/tps_sumg.shp'),
        'oilgas_vect': '#data/usgs/oilgas/oilgas.shp',

        'national_borders_source': ('HIU.State.Gov',
            '/Users/ztessler/data/HIU.State.Gov_National_Boundaries/countries.json'),
        'per_capita_gdp_source': ('worldbank',
            '/Users/ztessler/data/GDP_per_capita_WorldBank/ca0453f8-8c4c-4825-b40b-1a1bcd139c6a_v2.csv'),
        'per_capita_gdp_rast': '#data/experiments/{exp}/per_capita_gdp{ver}.{ext}',

        'pop_growth_source': ('un','http://esa.un.org/unpd/wpp/DVD/Files/1_Indicators%20(Standard)/EXCEL_FILES/1_Population/WPP2015_POP_F01_1_TOTAL_POPULATION_BOTH_SEXES.XLS'),
        'pop_growth_data': '#downloads/un_pop_growth.xls',
        'storm_surge_source': ('unisdr', 'http://data.hdx.rwlabs.org/dataset/87ce9e07-4914-49e6-81cc-3e4913d1ea02/resource/9d30760e-292f-4e81-9f5f-8a526977aa68/download/SS-world.zip'),
        'storm_surge_zip': '#downloads/unisdr_storm_surge.zip',
        'storm_surge_vect': '#data/unisdr/storm_surge/storm_surge.shp',

        'basins': '#data/basins{ver}.{ext}',
        'basins30': '#data/basins30{ver}.{ext}',
        'basins30cells': '#data/basins30cells{ver}.{ext}',
        'reservoirs': '#data/experiments/{exp}/reservoir{ver}.pd',
        'discharge': '#data/experiments/{exp}/discharge{ver}.pd',
        'airtemp': '#data/experiments/{exp}/airtemp{ver}.pd',
        'groundwater': '#data/experiments/{exp}/groundwater{ver}.pd',
        'ice': '#data/experiments/{exp}/ice{ver}.pd',
        'lithology': '#data/experiments/{exp}/lithology{ver}.pd',
        'per_capita_gdp': '#data/experiments/{exp}/per_capita_gdp{ver}.pd',
        'relief': '#data/experiments/{exp}/relief{ver}.pd',
        'pop_dens': '#data/experiments/{exp}/pop_dens{ver}.pd',

        'ssp_pop_source': ('ssp', '/Users/ztessler/data/SSP_pop_gdp_Murakami/population_ssp{ssp}.csv'),
        'ssp_pop': '#data/ssp/pop_ssp{ssp}.{ext}',
        'delta_ssp_pops': '#data/ssp/delta_ssp_pops.pd',
        'ssp_gdp_source': ('ssp', '/Users/ztessler/data/SSP_pop_gdp_Murakami/gdp_ssp{ssp}.csv'),
        'ssp_gdp': '#data/ssp/gdp_ssp{ssp}.{ext}',
        'delta_ssp_gdps': '#data/ssp/delta_ssp_gdps.pd',
        'delta_ssp_gdps_adj': '#data/experiments/{exp}/delta_ssp_gdps_adj.pd',
        'delta_ssp_percap_gdps': '#data/ssp/delta_ssp_percap_gdps.pd',
        'delta_ssp_percap_gdps_adj': '#data/experiments/{exp}/delta_ssp_percap_gdps_adj.pd',

        'storm_surge': '#data/experiments/{exp}/surge_return_levels.pd',
        'surge_populations': '#data/experiments/{exp}/surge_pop_exposure.pd',
        'surge_annual_exposure': '#data/experiments/{exp}/surge_annual_exposure.pd',
        'surge_risk': '#data/experiments/{exp}/surge_risk.pd',
        'surge_percap_risk': '#data/experiments/{exp}/surge_percap_risk.pd',

        'surge_annual_exposure_plot': '#figures/{exp}/surge_exposure_trend/{delta}_surge_annual_exposure_pop_trends.{ext}',
        'surge_annual_exposure_comparison_plot': '#figures/joint/{scenarios}/surge_exposure_trend/{delta}_surge_annual_exposure_pop_trends_{scenarios}.{ext}',
        'surge_annual_exposure_comparison_multidelta_plot': '#figures/joint/{scenarios}/surge_exposure_trend/alldelta_surge_annual_exposure_pop_trends_{scenarios}.{ext}',
        'surge_annual_exposure_ranges': '#data/experiments/joint/surge_annual_exposure_experiment_ranges.pd',

        'dis_future_source': ('isimip', 'daisy:/data/ISIMIP/RGISresults[{gcm}]/Global/Discharge/Global_Discharge_{gcm}[RCP{rcp}]+dist_30min_dTS{year}.{ext}'),
        'dis_future_years': (2006, 2099),
        'dis_future_hist_source': ('isimip', 'daisy:/data/ISIMIP/RGISresults[{gcm}]/Global/Discharge/Global_Discharge_{gcm}+dist_30min_dTS{year}.{ext}'),
        'dis_future_hist_years': (1950, 2005),
        'dis_future_rcps': ['2p6', '8p5'],
        'dis_future_gcm': 'GFDL-ESM2M',
        'dis_future_tmp': '#data/isimip/Global_Discharge_{gcm}[RCP{rcp}]+dist_30min_dTS{year}.tmp.{ext}',
        'dis_future_ncs': '#data/isimip/Global_Discharge_{gcm}[RCP{rcp}]+dist_30min_dTS{year}.nc',
        # 'dis_future_ncs': '/Volumes/environmental_science/TesslerZ/data/isimip/Global_Discharge_{gcm}[RCP{rcp}]+dist_30min_dTS{year}.nc',
        'dis_future_annual': '#data/isimip/dis_future_{rcp}_{year}.pd',
        'dis_future_rcp': '#data/isimip/dis_future_{rcp}.pd',
        'dis_future': '#data/isimip/dis_future.pd',
        'dis_future_hist': '#data/isimip/dis_future_hist.pd',
        'dis_future_extremes_basins': '#data/experiments/{exp}/dis_future_extreme_zscore_basins.pd',
        'dis_future_hist_extremes_basins': '#data/experiments/{exp}/dis_future_hist_extreme_zscore_basins.pd',
        'dis_future_window_mean_dis': '#data/experiments/{exp}/dis_future_window_means.pd',
        'dis_future_hist_extremes': '#data/experiments/{exp}/dis_future_hist_extreme_zscore.pd',
        'dis_future_fut_extremes': '#data/experiments/{exp}/dis_future_fut_extreme_zscore.pd',
        'dis_future_extremes': '#data/experiments/{exp}/dis_future_extreme_zscore.pd',

        'waves_future_source': ('csiro', 'http://tds.csiro.au/thredds/dodsC/Global_wave_projections/{forecast}/CMIP5/{rcp}/{gcm}/ww3_outf_{yyyymm}.nc'),
        # 'waves_future_gcms': ['MRI-CGCM3', 'MIROC5', 'INMCM4', 'HadGEM2-ES', 'GFDL-CM3', 'CNRM-CM5', 'BCC-CSM1.1', 'ACCESS1.0'],
        'waves_future_gcms': ['GFDL-CM3'],
        # 'waves_future_forecasts': ['HISTORICAL', 'MID21C', 'END21C'],
        # 'waves_future_rcps': ['RCP4.5', 'RCP8.5'],
        'waves_future_scenarios': [('HISTORICAL', 'RCPnone'), ('MID21C', 'RCP4.5'), ('MID21C', 'RCP8.5'), ('END21C', 'RCP4.5'), ('END21C', 'RCP8.5')],
        'waves_future_refscenario': ('HISTORICAL', 'RCPnone'),
        'waves_future_nclist': '#data/waves/waves_future_nclist_{gcm}_{forecast}_{rcp}.txt',
        'waves_future_monthly': '#data/waves/{gcm}/{forecast}/{rcp}/waves_future_{gcm}_{forecast}_{rcp}_{yyyymm}.pd',
        'waves_future_rcp_data_pixels': '#data/waves/{gcm}/{forecast}/waves_future_{gcm}_{forecast}_{rcp}_pixels.pd',
        'waves_future_rcp_data': '#data/waves/{gcm}/{forecast}/waves_future_{gcm}_{forecast}_{rcp}.pd',
        'waves_future_rcp_zscores': '#data/waves/{gcm}/{forecast}/waves_future_{gcm}_{forecast}_{rcp}_zscore.pd',
        'waves_future_forecast_zscores': '#data/waves/{gcm}/{forecast}/waves_future_{gcm}_{forecast}_zscore.pd',
        'waves_future_gcm_zscores': '#data/waves/{gcm}/waves_future_{gcm}_zscore.pd',
        'waves_future_extremes_stats': '#data/waves/waves_future_extreme_zscore_stats.pd',
        'waves_future_extremes': '#data/waves/waves_future_extreme_zscore.pd',
        # 'waves_future_extremes': '#data/experiments/{exp}/waves_future_extreme_zscore.pd',
        'waves_future_delta_indices': '#data/waves/delta_indices.json',

        'hazards_future': '#data/experiments/{exp}/hazard_scores.pd',



        'I': '#data/experiments/{exp}/bqart_I.pd',
        'Te': '#data/experiments/{exp}/bqart_Te.pd',
        'Eh': '#data/experiments/{exp}/bqart_Eh.pd',
        'B': '#data/experiments/{exp}/bqart_B.pd',
        'Qs': '#data/experiments/{exp}/bqart_Qs.pd',

        'groundwater_drawdown': '#data/experiments/{exp}/drawdown.pd',
        'groundwater_subsidence': '#data/experiments/{exp}/groundwater_subsidence.pd',

        'oilgas': '#data/experiments/{exp}/oilgas.pd',
        'oilgas_subsidence': '#data/experiments/{exp}/oilgas_subsidence.pd',
        'basin_ids': '#data/basin_ids.pd',
        'basin_mouths': '#data/basin_mouths.pd',
        'basin_areas': '#data/basin_areas.pd',
        'basin30_ids': '#data/basin30_ids.pd',
        'basin30_mouths': '#data/basin30_mouths.pd',

        'natural_subsidence': '#data/experiments/pristine/natural_subsidence.pd',
        'natural_subsidence_plot': '#figures/{exp}/natural_subsidence.png',
        'sed_aggradation': '#data/experiments/{exp}/sed_aggradation.pd',
        'rslr': '#data/experiments/{exp}/rslr.pd',
        'rslr_regress': '#data/experiments/{exp}/rslr_regress.{ext}',

        'sed_flux_comparison_plot': '#figures/joint/{scenarios}/sed_flux/sed_flux_{scenarios}.{ext}',
        'sed_flux_change_plot': '#figures/joint/{scenarios}/sed_flux/sed_flux_change_{expA}_to_{expB}.{ext}',
        'rslr_comparison_plot': '#figures/joint/{scenarios}/rslr/rslr_{scenarios}.{ext}',
        'rslr_change_plot': '#figures/joint/{scenarios}/rslr/rslr_change_{expA}_to_{expB}.{ext}',

        'vuln_source': ('tessler2015', '/Users/ztessler/data/deltas/idi_data.csv'),
        'vuln': '#data/experiments/{exp}/vuln.pd',
        'vuln_norm': 'unity',
        'econ_vuln': '#data/experiments/{exp}/econ_vuln.pd',
        'econ_capacity': '#data/experiments/{exp}/econ_capacity.pd',
        'vuln_adjustments': ['energy_cost'],
        'econ_vuln_adj': '#data/experiments/{exp}/econ_vuln_adj.pd',
        'econ_capacity_adj': '#data/experiments/{exp}/econ_capacity_adj.pd',
        'energy_cost_source': ('eia_outlook_2017', '/Users/ztessler/data/EIA/Macroeconomic_Indicators_Outlook2017.csv'),
        'energy_cost_index_key': '18-AEO2017.23.ref2017-d120816a', # Macroeconomic Indicators: Wholesale Price Index: Fuel and Power: Reference case
        'energy_cost_index_data': '#data/experiments/{exp}/energy_costs.pd',

        'risk_quadrants_plot_snapshot': '#figures/{exp}/risk_quadrants/risk_quadrants_snapshot.png',

        'basin_pixel_areas': '#data/basin_pixel_areas.tif',
        'upstream_zeros': '#data/upstream_zeros.pd',
        'upstream_ones': '#data/upstream_ones.pd',
        'delta_zeros': '#data/delta_zeros.pd',
        'delta_ones': '#data/delta_ones.pd',

        'srtm': 3,
        'eustatic_slr': 3.0,

        'name': 'Contemporary',
        'compare_with': ['accel-slr', 'double-reservoirs', 'zarfl-reservoirs'],
        }

experiments = {
        'contemp': defaults,
        'pristine': {
            'parent': 'contemp',
            'name': 'Pristine',
            'Te': defaults['upstream_zeros'],
            'Eh': defaults['upstream_ones'],
            'oilgas_source': ('zeros', None),
            'groundwater_source': ('zeros', None),
            'eustatic_slr': 1.5,
            'compare_with': ['contemp', 'accel-slr', 'double-reservoirs', 'zarfl-reservoirs'],
            },
        'accel-slr': {
            'parent': 'contemp',
            'name': 'Accelerated SLR',
            'eustatic_slr': 5.0,
            },
        'double-reservoirs': {
            'parent': 'contemp',
            'name': 'Doubled Reservoirs',
            'reservoir_adj_source': ('factor', 2.0),
            },
        'zarfl-reservoirs': {
            'parent': 'contemp',
            'name': 'Reservoir Growth (Zarfl, 2015)',
            'reservoir_adj_source': ('zarfl2015', '/Users/ztessler/data/Dams_Zarfl_2015/zarfl_2015_dams_data.xls'),
            },
        'rgis-reservoirs': {
            'parent': 'contemp',
            'name': 'RGIS reservoirs',
            'reservoir_source': ('rgis',),
            'reservoir_rast': '#data/rgis/reservoir{ver}.{ext}',
            'compare_with': ['contemp', 'zarfl-reservoirs', 'double-reservoirs'],
            },
        'SSPpops': {
            'parent': 'contemp',
            'name': 'SSP-based population growth scenarios',
            'compare_with': ['contemp'],
            # 'ssp_scenario': 3,
            'pop_growth_source': defaults['ssp_pop_source'],
            }
        }

# first fill in configs with parent values
done = False
while not done: # iterate until all parents and grandparents and great... have been filled in
    done = True
    updated_experiments = {}
    for experiment in experiments.keys():
        overrides = experiments[experiment]
        if 'parent' in overrides:
            done = False
            parent = overrides['parent']
            try:
                grandparent = experiments[parent]['parent']
            except KeyError:
                grandparent = None
            expanded = experiments[parent].copy()
            try:
                del expanded['compare_with']
            except KeyError:
                pass
            expanded.update(overrides)
            if grandparent:
                expanded['parent'] = grandparent
            else:
                del expanded['parent']
            updated_experiments[experiment] = expanded
        else:
            updated_experiments[experiment] = overrides
        updated_experiments[experiment].setdefault('compare_with', [])
    experiments = updated_experiments
# then set experiment directories and population year for output files
for experiment in experiments.keys():
    replacements = {
            'exp': experiment,
            'expA': '{expA}',
            'expB': '{expB}',
            'popyear': common['popyear'],
            'ver': '{ver}',
            'ext': '{ext}',
            'delta': '{delta}',
            'srtm': '{srtm}',
            'forecast': '{forecast}',
            'scenarios': '{scenarios}',
            'ssp': '{ssp}',
            'gcm': '{gcm}',
            'rcp': '{rcp}',
            'year': '{year}',
            'yyyymm': '{yyyymm}',
            }
    config = experiments[experiment]
    for name, path in config.items():
        if isinstance(path, tuple):
            pathitems = []
            for item in path:
                try:
                    pathitems.append(item.format(**replacements))
                except AttributeError:
                    pathitems.append(item)
            config[name] = tuple(pathitems)
        else:
            try:
                config[name] = path.format(**replacements)
            except AttributeError:
                pass
    experiments[experiment] = config


