import os
import geopandas
import rasterio
from affine import Affine
import cartopy.crs as ccrs
from cartopy.io.srtm import SRTM1Source, SRTM3Source, SRTMDownloader

def delta_srtm_composite(env, target, source):
    dname = env['delta']
    resolution=env['resolution']
    deltas = geopandas.GeoDataFrame.from_file(str(source[0])).set_index('Delta')
    minlon, minlat, maxlon, maxlat = deltas['geometry'][dname].bounds
    extent = (minlon, maxlon, minlat, maxlat)

    local_path_template = os.path.join(os.environ['HOME'], 'data', 'SRTM{resolution}', dname, '{y}{x}.hgt')
    downloader = SRTMDownloader(local_path_template)

    if resolution == 3:
        SRTMSource = SRTM3Source
    elif resolution == 1:
        SRTMSource = SRTM1Source
    else:
        raise ValueError('resolution must be 1 or 3')

    srtm = SRTMSource(downloader=downloader,
                       max_nx=(int(maxlon)-int(minlon)+1),
                       max_ny=(int(maxlat)-int(minlat)+1))
    raster = srtm.fetch_raster(ccrs.PlateCarree(), extent, resolution)
    image, extent = raster[0]
    pix = 1./60/60*resolution
    affine = Affine(pix, 0, extent[0],
                    0, -pix, extent[3])

    with rasterio.open(
            str(target[0]), 'w', driver='GTiff',
            width=image.shape[1], height=image.shape[0],
            crs={'init':'epsg:4326'}, transform=affine,
            count=1, dtype=image.dtype) as dst:
        dst.write(image, 1)

    return 0
