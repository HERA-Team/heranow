import redis
import numpy as np
from astropy.time import Time
from django.utils import timezone

from celery.decorators import task
from celery.utils.log import get_task_logger
from celery.task.schedules import crontab
from celery.decorators import periodic_task

from dashboard.models import Antenna, AutoSpectra

logger = get_task_logger(__name__)


@periodic_task(
    run_every=(crontab(minute="*/1")), name="reload_spectra", ignore_result=True,
)
def get_autospectra_from_redis():
    logger.info("Getting Spectra from Redis")
    redis_pool = redis.ConnectionPool(host="redishost", port=6379)
    with redis.Redis(connection_pool=redis_pool) as rsession:
        for antenna in Antenna.objects.all():
            d = rsession.get(f"auto:{antenna.ant_number:d}{antenna.polarization:s}")
            if d is not None:
                auto = np.frombuffer(d, dtype=np.float32).copy()
                break
        auto_size = auto.size
        # Generate frequency axis
        # Some times we have 6144 length inputs, others 1536, this should
        # set the length to match whatever the auto we got was
        NCHANS = int(8192 // 4 * 3)
        NCHANS_F = 8192
        NCHAN_SUM = NCHANS // auto_size
        NCHANS = auto_size
        frange = np.linspace(0, 250e6, NCHANS_F + 1)[1536 : 1536 + (8192 // 4 * 3)]
        # average over channels
        freqs = frange.reshape(NCHANS, NCHAN_SUM).sum(axis=1) / NCHAN_SUM

        timestamp = np.frombuffer(rsession["auto:timestamp"], dtype=np.float64)[0]
        timestamp = Time(timestamp, format="jd")
        timestamp = timestamp.datetime

        spectra = []
        for antenna in Antenna.objects.all():
            d = rsession.get(f"auto:{antenna.ant_number:d}{antenna.polarization:s}")
            if d is not None:
                auto = np.frombuffer(d, dtype=np.float32)[0:NCHANS].copy()

                eq_coeffs = rsession.hget(
                    f"eq:ant:{antenna.ant_number:d}{antenna.polarization:s}".encode(),
                    "values",
                )
                if eq_coeffs is not None:
                    eq_coeffs = np.fromstring(
                        eq_coeffs.decode("utf-8").strip("[]"), sep=","
                    )
                    if eq_coeffs.size == 0:
                        eq_coeffs = np.ones_like(auto)
                else:
                    eq_coeffs = np.ones_like(auto)

                auto_spectra = AutoSpectra(
                    antenna=antenna,
                    spectra=auto.tolist(),
                    frequencies=freqs.tolist(),
                    time=timestamp,
                    eq_coeffs=eq_coeffs.tolist(),
                )
                spectra.append(auto_spectra)

        AutoSpectra.objects.bulk_create(spectra, ignore_conflicts=True)
    logger.info("Done")
    return
