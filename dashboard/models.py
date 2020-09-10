import datetime

from astropy.time import Time

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy
from django.contrib.postgres.fields import ArrayField

# Create your models here.


class Antenna(models.Model):
    ant_number = models.IntegerField()
    ant_name = models.CharField(max_length=5)
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
        indexes = [
            models.Index(fields=["ant_number", "polarization"]),
            models.Index(fields=["ant_name"]),
        ]

    def __str__(self):
        return f"{self.ant_name} pol:{self.polarization} built:{self.constructed}"


def _get_dummy_default():
    return [1]


class AutoSpectra(models.Model):
    antenna = models.ForeignKey(Antenna, on_delete=models.CASCADE)
    spectra = ArrayField(models.FloatField())
    frequencies = ArrayField(models.FloatField())
    time = models.DateTimeField("Status Time")
    eq_coeffs = ArrayField(models.FloatField(), default=_get_dummy_default)
    frequencies_downsampled = ArrayField(
        models.FloatField(), default=_get_dummy_default
    )
    spectra_downsampled = ArrayField(models.FloatField(), default=_get_dummy_default)

    def is_recent(self):
        now = timezone.now()
        return now - datetime.TimeDelta(days=1) <= self.time <= now

    is_recent.admin_order_field = "time"
    is_recent.boolean = True
    is_recent.short_description = "Recent Spectra?"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["antenna", "time"], name="One antpol auto per time"
            ),
        ]
        indexes = [
            models.Index(fields=["antenna", "time"]),
        ]

    def clean(self):
        if len(self.frequencies) != len(self.spectra):
            raise ValidationError(
                "Input frequencies and spectra must be the same length."
            )
        if len(self.frequencies_downsampled) != len(self.spectra_downsampled):
            raise ValidationError(
                "Input downsampled frequencies and spectra must be the same length."
            )


class AprioriStatus(models.Model):
    antenna = models.ForeignKey(Antenna, on_delete=models.CASCADE)
    time = models.DateTimeField("Status Time")

    _mc_apriori_mapping = {
        "dish_maintenance": "DhM",
        "dish_ok": "DhO",
        "RF_maintenance": "RFM",
        "RF_ok": "RFO",
        "digital_maintenance": "DiM",
        "digital_ok": "DiO",
        "calibration_maintenance": "CaM",
        "calibration_ok": "CaO",
        "calibration_triage": "CaT",
    }

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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["antenna", "time"], name="One antpol apriori per time"
            ),
        ]
        indexes = [
            models.Index(fields=["antenna", "time"]),
        ]

    def observation_ready(self):
        return self.apriori_status in {
            self.AprioriStatusList.DIGITAL_OK,
            self.AprioriStatusList.CALIBRATION_MAINTENANCE,
            self.AprioriStatusList.CALIBRATION_OK,
            self.AprioriStatusList.CALIBRATION_TRIAGE,
        }

    def __str__(self):
        return f"{self.antenna.ant_name} staus: {self.get_apriori_status_display()}"


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

    _fem_mapping = {
        "antenna": "ANT",
        "load": "LOAD",
        "noise": "NOISE",
    }

    class FemSwitchStates(models.TextChoices):
        ANTENNA = "ANT", gettext_lazy("Antenna")
        LOAD = "LOAD", gettext_lazy("Load")
        NOISE = "NOISE", gettext_lazy("Noise")

    fem_switch = models.CharField(
        max_length=5, choices=FemSwitchStates.choices, null=True
    )

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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["antenna", "time"], name="One antpol status per time"
            ),
        ]
        indexes = [
            models.Index(fields=["antenna", "time"]),
            models.Index(fields=["snap_hostname", "snap_channel_number"]),
        ]


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
            models.UniqueConstraint(
                fields=["hostname", "time"], name="one snap status per time"
            ),
        ]
        indexes = [
            models.Index(fields=["hostname", "time"]),
            models.Index(fields=["hostname", "snap_loc_num"]),
        ]

    def __str__(self):
        return f"{self.hostname} observed: {self.time}"


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
                fields=["time", "hostname", "input_number"],
                name="unique snap spectra per time",
            ),
        ]
        indexes = [
            models.Index(fields=["hostname", "time"]),
            models.Index(fields=["hostname", "input_number"]),
        ]

    def __str__(self):
        return f"{self.hostname} #{self.input_number} observed: {self.time}"


class HookupNotes(models.Model):
    """
    Description of the HookupNotes table formatted from HERA M&C database.

    Field definitions are defined below

    time : Datetime Column
        The timestamp of the note
    ant_number : Integer Column
        The antenna number with which the note is associated
    part : String Column
        The part identification string of the note
    note : Text Column
        The modification noted in M&C
    """

    time = models.DateTimeField()
    ant_number = models.IntegerField()
    part = models.CharField(max_length=200)
    note = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["time", "ant_number", "part"], name="unique part note per time",
            ),
        ]

    def __str__(self):
        return f"Antenna: {self.ant_number} Part: {self.part} Date: {self.time}"


class CommissioningIssue(models.Model):
    """
    Description of the Commisioning issues table.


    Used to track nighlty notebooks and more.


    julian_date : Integer Column
        The JD of the observation
    number : Integer Column
        The issue number, if None, issue does not exist
    related_issues : Array Column
        Other Issues reference in this one. Stored as an array of issue number
    labels : Array Column
        Labels given to the github issue. Stored as an array of strings.
    new_issues : Integer Column
        Number of new issues opened on this day

    """

    julian_date = models.IntegerField()
    number = models.IntegerField(null=True, blank=True)
    related_issues = ArrayField(models.IntegerField(), null=True, blank=True)
    labels = ArrayField(models.CharField(max_length=200), null=True, blank=True)
    new_issues = models.IntegerField(null=True, blank=True)

    def nightly_notebook_date(self):
        return self.julian_date

    def rfi_notebook_date(self):
        obs_date = Time(self.julian_date, format="jd")
        return obs_date.isot.split("T")[0].replace("-", "")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["julian_date"], name="julian date"),
        ]


class XengChannels(models.Model):
    """
    Description of the  Xeng Channel mapping table.

    number : Integer Column
        The xeng's assigned number.
    chans : ArrayField
        The array of integers of channel numbers assigned to the xeng.

    """

    time = models.DateTimeField()
    number = models.IntegerField()
    chans = ArrayField(models.IntegerField())

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["number", "chans"], name="xengs must have disjoint channels."
            )
        ]

    def __str__(self):
        return f"xeng: {self.number} chans: {self.chans[0]}...{self.chans[-1]}"


class AntToSnap(models.Model):
    """
    Description of Antenna to Snap mapping table.

    time : DateTimeField
        Time the mapping was last updated
    antenna : Antenna class object
        Instance of the antenna associated with the snap
    snap_hostname : Text Column
        The snap name associated.
    chan : Integer Column
        The snap channel into which the antenna is plugged.

    """

    time = models.DateTimeField("Snap mapping timestamp")
    antenna = models.ForeignKey(Antenna, on_delete=models.CASCADE)
    snap_hostname = models.CharField(max_length=200)
    chan = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["time", "antenna"], name="One ant to snap mapping per time"
            )
        ]

    def __str__(self):
        return f"{str(self.antenna.ant_number)}{str(self.antenna.polarization)} snap: {self.snap_hostname}:{self.chan}"


class SnapToAnt(models.Model):
    """
    Description of the Snap to Antenna mapping table.

    time : DateTimeField
        The time associatd with the mapping
    snap_hostname : Text Column
        The Name of the snap
    node : Integer Column
        The Node number of the snap
    snap : Integer Column
        The Snap number of the snap
    ants : Array Field
        An array of antenna nemes associated with the snap.
    inds : Array Field
        Array of correlator antenna indices associated with the snap

    """

    time = models.DateTimeField("Snap mapping timestamp")
    snap_hostname = models.CharField(max_length=200)
    node = models.IntegerField(null=True, blank=True)
    snap = models.IntegerField(null=True, blank=True)
    ants = ArrayField(models.CharField(max_length=6))
    inds = ArrayField(models.IntegerField(), null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["time", "snap_hostname"],
                name="One snap to ant mappering per time",
            )
        ]
        ordering = ["node", "snap"]

    def __str__(self):
        return f"host: {self.snap_hostname} ants: {self.ants} inds: {self.inds}"


# class MCSummary(models.Model):
#     """A front page summary table from M&C.
#
#     last_obs : DateTime Column
#         The date of the last recorded observation
#     n_files : Integer Column
#         The Number of files recorded.
#     node_pings : Array of Char Columns
#         List of Nodes and number of pings "Node#:Ping_Count"
#     is_recording : BooleanField
#         Boolean Flag if correlator state is set to recording.
#
#     """
#
#     last_obs = models.DateTimeField()
#     n_files = models.IntegerField()
#     node_pings = ArrayField(models.CharField(max_length=100))
#     is_recording = models.BooleanField()
