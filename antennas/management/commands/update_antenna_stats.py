import logging  # noqa
from hera_corr_cm import HeraCorrCM

from django.core.management.base import BaseCommand, CommandError
from antennas.models import Antenna, AntennaStatus

logger = logging.getLogger(__name__)


def serial_list_to_string(serial_number_list):
    """
    Convert the native FEM/PAM Bytewise serial number to a string.

    Adapted from HERA-Team/hera_mc/correlator.py

    Parameters
    ----------
    serial_number_list : list of ints
        Bytewise serial number of a FEM or PAM

    Returns
    -------
    str
        decoded string serial number

    """
    try:
        serial_str = ""
        for int_val in serial_number_list:
            hex_val = hex(int_val)[2:]
            # str_val = bytes.fromhex(hex_val).decode('ascii')
            str_val = hex_val
            serial_str += str_val

        return serial_str
    except Exception:
        return None


class Command(BaseCommand):
    help = "Read data from redis databse and update local django database."

    def add_arguments(self, parser):
        parser.add_argument("--redishost", default="redishost")
        parser.add_argument("--redisport", default=6379)

    def handle(self, *args, **options):
        corr_cm = HeraCorrCM(redishost=options["redishost"], logger=logger)
        ant_stats = corr_cm.get_ant_status()
        bulk_add = []
        for antpol, stats in ant_stats.items():
            try:
                antenna = Antenna.objects.get(
                    ant_number=int(antpol.split(":")[0]),
                    polarization=antpol.split(":")[1],
                )
            except Antenna.DoesNotExist:
                continue
            for key in stats:
                if stats[key] == "None":
                    stats[key] = None

            if stats["fem_id"] is not None and stats["fem_id"] != -1:
                fem_id = serial_list_to_string(stats["fem_id"])
            else:
                fem_id = None

            if stats["pam_id"] is not None and stats["pam_id"] != -1:
                pam_id = serial_list_to_string(stats["pam_id"])
            else:
                pam_id = None
            if antenna.polarization == "n":
                fem_lna_power = stats["fem_n_lna_power"]
            elif antenna.polarization == "e":
                fem_lna_power = stats["fem_e_lna_power"]

            antenna_status = AntennaStatus(
                antenna=antenna,
                time=stats["timestamp"],
                snap_hostname=stats["f_host"],
                snap_channel_number=stats["host_ant_id"],
                adc_mean=stats["adc_mean"],
                adc_rms=stats["adc_rms"],
                adc_power=stats["adc_power"],
                pam_atten=stats["pam_atten"],
                pam_power=stats["pam_power"],
                pam_voltage=stats["pam_voltage"],
                pam_current=stats["pam_current"],
                pam_id=pam_id,
                fem_voltage=stats["fem_voltage"],
                fem_current=stats["fem_current"],
                fem_id=fem_id,
                fem_imu=[stats["fem_imu_theta"], stats["fem_imu_phi"]],
                fem_temp=stats["fem_temp"],
                fem_lna_power=fem_lna_power,
                fft_overflow=stats["fft_of"],
                eq_coeffs=stats["eq_coeffs"],
                adc_hist=stats["histogram"],
            )
            bulk_add.append(antenna_status)

        AntennaStatus.objects.bulk_create(bulk_add, ignore_conflicts=True)
