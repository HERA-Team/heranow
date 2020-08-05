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
    antpos_enu = ArrayField(models.FloatField(), size=3, default=list)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ant_number", "polarization"], name="unique antpol"
            ),
            models.CheckConstraint(
                check=models.Q(ant_number__lte=350), name="ant_num_lte_350"
            ),
        ]

    def __str__(self):
        return f"Antenna {self.ant_number}{self.polarization}"


class AutoSpectra(models.Model):
    antenna = models.ForeignKey(Antenna, on_delete=models.CASCADE)
    spectra = ArrayField(models.FloatField())
    frequencies = ArrayField(models.FloatField())
    time = models.DateTimeField("Status Time")

    def is_recent(self):
        now = timezone.now()
        return now - datetime.TimeDelta(days=1) <= self.time <= now

    is_recent.admin_order_field = "time"
    is_recent.boolean = True
    is_recent.short_description = "Recent Spectra?"

    def clean(self):
        if len(self.frequencies) != len(self.spectra):
            raise ValidationError(
                "Input frequencies and spectra must be the same length."
            )
        if len(self.frequencies) != len(self.eq_coeffs):
            raise ValidationError(
                "Input frequencies and eq_coeffs must be the same length."
            )


class AprioriStatus(models.Model):
    antenna = models.ForeignKey(Antenna, on_delete=models.CASCADE)
    time = models.DateTimeField("Status Time")

    class AprioriStatusList(models.TextChoices):
        DISH_MAINTENANCE = "DhM", gettext_lazy("Dish Maintenance")
        DISH_OK = "DhO", gettext_lazy("Dish OK")
        RF_MAINTENANCE = "RFM", gettext_lazy("RF Maintenance")
        RF_OK = "RFO", gettext_lazy("RF OK")
        DIGITAL_MAINTENANCE = "DiM", gettext_lazy("Digital Maintenance")
        DIGITAL_OK = "DiO", gettext_lazy("Digital OK")
        CALIBRATION_MAINTENANCE = "CaM", gettext_lazy("Calibration Maintenance")
        CALIBRATION_OK = "CaO", gettext_lazy("Calibration OK")
        CALIBRATION_TRIAGE = "CaT", gettext_lazy("Calibration Triage")

    apriori_status = models.CharField(max_length=3, choices=AprioriStatusList.choices)

    def observation_ready(self):
        return self.apriori_status in {
            self.AprioriStatus.DIGITAL_OK,
            self.AprioriStatus.CALIBRATION_MAINTENANCE,
            self.AprioriStatus.CALIBRATION_OK,
            self.AprioriStatus.CALIBRATION_TRIAGE,
        }


class AntennaStatus(models.Model):
    antenna = models.ForeignKey(Antenna, on_delete=models.CASCADE)
    time = models.DateTimeField("Status Time")
    snap_hostname = models.CharField(max_length=200, blank=True, null=True)
    snap_channel_number = models.PositiveSmallIntegerField(blank=True, null=True)
    fem_id = models.CharField(max_length=200, blank=True, null=True)
    fem_lna_power = models.BooleanField(blank=True, null=True)
    # fem IMU Theta and Phi
    fem_imu = ArrayField(models.FloatField(), 2, blank=True, null=True)
    fem_temp = models.FloatField(blank=True, null=True)
    fft_overflow = models.BooleanField(blank=True, null=True)
    eq_coeffs = ArrayField(models.FloatField(), blank=True, null=True)
    # adc histograms first row centers, second row values
    adc_hist = ArrayField(ArrayField(models.FloatField()), blank=True, null=True)

    class FemSwitchStates(models.TextChoices):
        ANTENNA = "ANT", gettext_lazy("Antenna")
        LOAD = "LOAD", gettext_lazy("Load")
        NOISE = "NOISE", gettext_lazy("Noise")

    fem_switch = models.CharField(max_length=5, choices=FemSwitchStates.choices)

    def status_is_recent(self):
        now = timezone.now()
        return now - datetime.TimeDelta(days=1) <= self.time <= now

    status_is_recent.admin_order_field = "time"
    status_is_recent.boolean = True
    status_is_recent.short_description = "Recent Status?"

    def clean(self):
        if (
            self.snap_channel_number is not None
            and not 0 <= self.snap_channel_number <= 7
        ):
            raise ValidationError("snap_channel_number must be in the range [0,7].")
