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
    constructed = models.BooleanField(default=False)

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
    """
    Definition of antenna status table (based on SNAP info).

    Very Similar to the Atenna Status table from HERA MC.
    Listed below are the columns in the table.


    antenna : Antenna Instance
       An instance of the Antenna Class. The antenna number and polarization.
    time : Datetime Column
        GPS time of the antenna status data, floored. Part of primary_key.
    snap_hostname : String Column
        SNAP hostname.
    snap_channel_number : Integer Column
        The SNAP ADC channel number (0-7) to which this antenna is connected.
    adc_mean : Float Column
        Mean ADC value, in ADC units.
    adc_rms : Float Column
        RMS ADC value, in ADC units.
    adc_power : Float Column
        Mean ADC power, in ADC units squared.
    pam_atten : Integer Column
        PAM attenuation setting for this antenna, in dB. (Integer)
    pam_power : Float Column
        PAM power sensor reading for this antenna, in dBm.
    pam_voltage : Float Column
        PAM voltage sensor reading for this antenna, in Volts.
    pam_current : Float Column
        PAM current sensor reading for this antenna, in Amps.
    pam_id : String Column
        Serial number of this PAM.
    fem_voltage : Float Column
        FEM voltage sensor reading for this antenna, in Volts.
    fem_current : Float Column
        FEM current sensor reading for this antenna, in Amps.
    fem_id : String Column
        Serial number of this FEM.
    fem_switch : String Column
        Switch state for this FEM. Options are: {'antenna', 'load', 'noise'}
    fem_lna_power : Boolean Column
        Power state of this FEM (True if powered).
    fem_imu : Array Column
        IMU-reported theta and phi, in degrees.
    fem_temp : Float Column
        EM temperature sensor reading for this antenna in degrees Celsius.
    fft_overflow : Boolean Column
        Indicator of an FFT overflow, True if there was an FFT overflow.
    eq_coeffs : Array Column
        Digital EQ coefficients for this antenna,
    adc_hist : Array of Array Column
        2D array of [[ADC histogram bin centers],[ADC histogram counts]]

    """

    antenna = models.ForeignKey(Antenna, on_delete=models.CASCADE)
    time = models.DateTimeField("Status Time")

    snap_hostname = models.CharField(max_length=200, blank=True, null=True)
    snap_channel_number = models.PositiveSmallIntegerField(blank=True, null=True)

    adc_mean = models.FloatField(blank=True, null=True)
    adc_rms = models.FloatField(blank=True, null=True)
    adc_power = models.FloatField(blank=True, null=True)

    pam_atten = models.IntegerField(blank=True, null=True)
    pam_power = models.FloatField(blank=True, null=True)
    pam_voltage = models.FloatField(blank=True, null=True)
    pam_current = models.FloatField(blank=True, null=True)
    pam_id = models.CharField(max_length=200, blank=True, null=True)

    fem_voltage = models.FloatField(blank=True, null=True)
    fem_current = models.FloatField(blank=True, null=True)
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


class SnapStatus(models.Model):
    """
    Definition of SNAP status table.

    Must match  SNAPStatus table from HERA MC.
    Listed below are the columns in the table.


    time : Datetime Column
        Time of the snap status data, floored.
    hostname : String Column
        SNAP hostname.
    node : Integer Column
        Node number.
    snap_loc_num : Integer Column
        SNAP location number.
    serial_number : String Column
        Serial number of the SNAP board.
    psu_alert : Boolean Column
        True if SNAP PSU (aka PMB) controllers have issued an alert.
        False otherwise.
    pps_count : BigInteger Column
        Number of PPS pulses received since last programming cycle.
    fpga_temp : Float Column
        Reported FPGA temperature in degrees Celsius.
    uptime_cycles : BigInteger Column
        Multiples of 500e6 ADC clocks since last programming cycle.
    last_programmed_time :  BigInteger Column
        Last time this FPGA was programmed in floored gps seconds.
    """

    time = models.DateTimeField("Status Time")
    hostname = models.CharField(max_length=200)
    node = models.IntegerField(blank=True, null=True)
    snap_loc_num = models.IntegerField(blank=True, null=True)
    serial_number = models.CharField(max_length=200, blank=True, null=True)
    psu_alert = models.BooleanField(blank=True, null=True)
    pps_count = models.BigIntegerField(blank=True, null=True)
    fpga_temp = models.FloatField(null=True, blank=True)
    uptime_cycles = models.BigIntegerField(null=True, blank=True)
    last_programmed_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["hostname"], name="unique hostname"),
        ]

    def __str__(self):
        return f"SnapStatus {self.hostname} {self.time}"


class SnapSpectra(models.Model):
    """
    Description of a SnapRF status table. Pulled from hera_corr_cm directly.

    Below is a list of columns in the table

    time : DateTime Field
        The time of the status
    hostname : String Column
        The name of the host
    input_number : Integer Column
        The snap input number.
    eq_coeffs : Array Column
        The equalization coefficients for the snap spectrum
    spectra : Array Column
        The autocorrelation spectrum taken directly from the snap
    adc_hist : Array of Array Column
        2D array of [[ADC histogram bin centers],[ADC histogram counts]]

    """

    time = models.DateTimeField()
    hostname = models.CharField(max_length=200)
    input_number = models.IntegerField()
    spectra = ArrayField(models.FloatField(), blank=True, null=True)
    eq_coeffs = ArrayField(models.FloatField(), blank=True, null=True)
    # adc histograms first row centers, second row values
    adc_hist = ArrayField(ArrayField(models.FloatField()), blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["hostname", "input_number"], name="unique snap input"
            ),
        ]

    def __str__(self):
        return f"SnapSpectra {self.hostname} #{self.input_number}"
