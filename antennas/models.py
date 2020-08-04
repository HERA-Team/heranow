import datetime

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy
from django.contrib.postgres.fields import ArrayField

# Create your models here.

class Antenna(models.Model):
    ant_number = models.IntegerField()
    polarization = models.CharField(max_length=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["ant_number", "polarization"], name="unique antpol"),
            models.CheckConstraint(check=models.Q(ant_number__lte=350), name="ant_num_lte_350"),
        ]

    def __str__(self):
        return f"Antenna {self.ant_number}{self.polarization}"


class AntennaStatus(models.Model):
    antenna = models.ForeignKey(Antenna, on_delete=models.CASCADE)
    spectra = ArrayField(models.FloatField())
    frequencies = ArrayField(models.FloatField())
    time = models.DateTimeField("Status Time")
    snap_hostname = models.CharField(max_length=200)
    snap_channel_number = models.PositiveSmallIntegerField()
    fem_id = models.CharField(max_length=200)
    fem_lna_power = models.BooleanField()
    # fem IMU Theta and Phi
    fem_imu = ArrayField(models.FloatField(), 2)
    fem_temp = models.FloatField()
    fft_overflow = models.BooleanField()
    eq_coeffs = ArrayField(models.FloatField())
    # adc histograms first row centers, second row values
    adc_hist = ArrayField(ArrayField(models.FloatField()))

    class FemSwitchStates(models.TextChoices):
        ANTENNA = "ANT", gettext_lazy("Antenna")
        LOAD = "LOAD", gettext_lazy("Load")
        NOISE = "NOISE", gettext_lazy("Noise")

    fem_switch = models.CharField(max_length=5, choices=FemSwitchStates.choices)

    class AprioriStatus(models.TextChoices):
        DISH_MAINTENANCE = "DhM", gettext_lazy("Dist Maintenance")
        DISH_OK = "DhO", gettext_lazy("Dist OK")
        RF_MAINTENANCE = "RFM", gettext_lazy("RF Maintenance")
        RF_OK = "RFO", gettext_lazy("RF OK")
        DIGITAL_MAINTENANCE = "DiM", gettext_lazy("Digital Maintenance")
        DIGITAL_OK = "DiO", gettext_lazy("Digital OK")
        CALIBRATION_MAINTENANCE = "CaM", gettext_lazy("Calibration Maintenance")
        CALIBRATION_OK = "CaO", gettext_lazy("Calibration OK")
        CALIBRATION_TRIAGE = "CaT", gettext_lazy("Calibration Triage")

    apriori_status = models.CharField(max_length=3, choices=AprioriStatus.choices)

    def observation_ready(self):
        return self.apriori_status in {
            self.AprioriStatus.DIGITAL_OK,
            self.AprioriStatus.CALIBRATION_MAINTENANCE,
            self.AprioriStatus.CALIBRATION_OK,
            self.AprioriStatus.CALIBRATION_TRIAGE,
        }

    def status_is_recent(self):
        now = timezone.now()
        return now - datetime.TimeDelta(days=1) <= self.time <= now

    status_is_recent.admin_order_field = 'time'
    status_is_recent.boolean = True
    status_is_recent.short_description = 'Recent Status?'

    def clean(self):
        if len(self.frequencies) != len(self.spectra):
            raise ValidationError(
                "Input frequencies and spectra must be the same length."
            )
        if len(self.frequencies) != len(self.eq_coeffs):
             raise ValidationError(
                 "Input frequencies and eq_coeffs must be the same length."
             )
        if not 0 <= self.snap_channel_number <= 7:
            raise ValidationError(
                "snap_channel_number must be in the range [0,7]."
            )
