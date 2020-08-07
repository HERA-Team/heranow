import redis
import numpy as np
from astropy.time import Time
from django.utils import timezone

from django.core.management.base import BaseCommand, CommandError
from antennas.models import Antenna, AutoSpectra


class Command(BaseCommand):
    help = "Read data from redis databse and update local django database."

    def add_arguments(self, parser):
        parser.add_argument("--redishost", default="redishost")
        parser.add_argument("--redisport", default=6379)

    def handle(self, *args, **options):
        redis_pool = redis.ConnectionPool
        redis_pool = redis.ConnectionPool(
            host=options["redishost"], port=options["redisport"],
        )
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

            t_plot_jd = np.frombuffer(rsession["auto:timestamp"], dtype=np.float64)[0]
            t_plot = Time(t_plot_jd, format="jd")
            timestamp = t_plot.datetime

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

                    # divide out the equalization coefficients
                    # eq_coeffs are stored as a length 1024 array but only a
                    # single number is used. Taking the median to not deal with
                    # a size mismatch
                    eq_coeffs = np.median(eq_coeffs)
                    auto /= eq_coeffs ** 2

                    auto_spectra = AutoSpectra(
                        antenna=antenna,
                        spectra=auto.tolist(),
                        frequencies=freqs.tolist(),
                        time=timestamp,
                    )
                    auto_spectra.save()
