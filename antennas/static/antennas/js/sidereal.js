<!--
// Begin Script "sidereal.js"

/*	SIDEREAL CLOCK
Local Sidereal Clock for Windows Desktop By James Melatis
webmaster@indigotide.com
Click on set-up button to get a prompt window
Set longitude to decimalized local longitude to compute offset for Local Sidereal Time
Setting will round automatically to 7 decimal places
7 decimal places puts you within 1/2" at the equator (0.0004 arc seconds)
and even less closer to the poles
longitude = 0 = Greenwich Mean Sidereal Time (GMST)
longitude negative = West longitude offset
longitude positive = East longitude offset
EXAMPLE: West Longitude 117° 31' 51.71988" = -117.5310333°
*/ 

// execute this when the form loads

function loadUserSetting()
{	DefaultLongitude = -74.0060;	// Put YOUR default local longitude here...

clock.longitude.value = DefaultLongitude;	

document.getElementById( "longitude" ).readOnly = true;	// no typing in displays allowed
document.getElementById( "degrees" ).readOnly = true;
document.getElementById( "minutes" ).readOnly = true;
document.getElementById( "seconds" ).readOnly = true;
document.getElementById( "meridian" ).readOnly = true;
document.getElementById( "degrees2" ).readOnly = true;
document.getElementById( "meridian2" ).readOnly = true;
document.getElementById( "date" ).readOnly = true;	
document.getElementById( "utc" ).readOnly = true;
document.getElementById( "gmst" ).readOnly = true;
document.getElementById( "day" ).readOnly = true;
document.getElementById( "angle" ).readOnly = true;
document.getElementById( "lst" ).readOnly = true;

var InputValue = parseFloat( clock.longitude.value );
UpdateLongitude( InputValue );	// update all longitude displays


}

function UpdateClock()	//loop to keep time displays current 
{
var long = parseFloat (clock.longitude.value);	// get longitude variable from current form INPUT text value
// and convert to floating point number

var now = new Date();	// get current date & time from computer clock

var date = now.toLocaleString();	// format date as local full date and 12 hour clock
var utc = now.toUTCString();	// format utc as UTC date & time

var beg = new Date( now.getUTCFullYear() - 1, 11, 31 );	// get last day of previous year in milliseconds
var day = Math.floor( ( now - beg ) / 86400000 );	// compute integer day of year (86400000 ms/day) 

var mst = getGMST( now );	// get adjusted GMST in degrees for current system time 
var mstAngle = mst;	// save for GMST Angle display

// compute integer GMST hour angle deg min sec
var gmstdeg = Math.floor( mstAngle );	// get integer GMST hour angle degrees right ascension of vernal equinox

mstAngle = mstAngle - gmstdeg;	// get integer GMST hour angle minutes right ascension of vernal equinox
mstAngle = mstAngle * 60;
var gmstmin = Math.floor( mstAngle );

mstAngle = mstAngle - gmstmin;	// get integer GMST hour angle seconds right ascension of vernal equinox
mstAngle = mstAngle * 60;
var gmstsec = Math.floor( mstAngle );

var lst = mst + long;	// now we know GMST so just add local longitude offset

if( lst > 0.0 )	// circle goes round and round, adjust LST if < 0 or > 360 degrees
{
while( lst > 360.0 )
lst -= 360.0;
}
else
{
while( lst < 0.0 )
lst += 360.0;
}

var ras = lst;	// save LST degrees right ascension for hour angle display

lst = lst / 15.0;	// change LST from degrees to time units (15 deg/hour)
mst = mst / 15.0;	// change MST from degrees to time units (15 deg/hour)

// compute integer LST hour angle deg min sec
var deg = Math.floor( ras );	// get integer hour angle degrees right ascension of vernal equinox

ras = ras - deg;	// get integer hour angle minutes right ascension of vernal equinox
ras = ras * 60;
var min = Math.floor( ras );

ras = ras - min;	// get integer hour angle seconds right ascension of vernal equinox
ras = ras * 60;
var sec = Math.floor( ras );

// compute local sidereal time hour minute second
hour = Math.floor( lst );	// get integer LST hour

lst = lst - hour;	// get integer LST minute
lst = lst * 60;
minute = Math.floor( lst );

lst = lst - minute;	//get integer LST second
lst = lst * 60;
second = Math.floor( lst ); 
// compute GMST time hours minutes seconds
hours = Math.floor( mst );	// get integer MST hours

mst = mst - hours;	// get integer MST minutes
mst = mst * 60;
minutes = Math.floor( mst );

mst = mst - minutes;	//get integer MST seconds
mst = mst * 60;
seconds = Math.floor( mst ); 

document.clock.date.value = " " + date;	// update "clock" form displays
document.clock.utc.value = " " + utc;
document.clock.gmstangle.value = " " + addZero( gmstdeg ) + "° " + addZero( gmstmin ) + "\' " + addZero( gmstsec ) + "\"";
document.clock.gmst.value = " " + addZero( hours ) + " : " + addZero( minutes ) + " : " + addZero( seconds );
document.clock.day.value = " " + day ;
document.clock.angle.value = " " + addZero( deg ) + "° " + addZero( min ) + "\' " + addZero( sec ) + "\"";
document.clock.lst.value = " " + addZero( hour ) + " : " + addZero( minute ) + " : " + addZero( second );

newtime = window.setTimeout("UpdateClock();", 1000);	// update all clock displays once per second
}


function addZero( n )	// adds leading zero if 1 digit number 
{
if( n < 10 )
{
return "0" + n;
}
else
return n;
}

// Function getGMST computes Mean Sidereal Time (J2000)
// Input: Current Date
// Returns: Adjusted Greenwich Mean Sidereal Time (GMST) in degrees

function getGMST( now )
{
var year = now.getUTCFullYear();	// get UTC from computer clock date & time (var now) 
var month = now.getUTCMonth() + 1;
var day = now.getUTCDate();
var hour = now.getUTCHours();
var minute = now.getUTCMinutes();
var second = now.getUTCSeconds();

if( month == 1 || month == 2 )
{
year = year - 1;
month = month + 12;
}

var lc = Math.floor( year/100 );	//integer # days / leap century
var ly = 2 - lc + Math.floor( lc/4 );	//integer # days / leap year
var y = Math.floor(365.25 * year);	//integer # days / year
var m = Math.floor(30.6001 * (month + 1));	//integer # days / month

// now get julian days since J2000.0 
var jd = ly + y + m - 730550.5 + day + (hour + minute/60.0 + second/3600.0)/24.0;

// julian centuries since J2000.0
var jc = jd/36525.0; 

// Greenwich Mean Sidereal Time (GMST) in degrees
var GMST = 280.46061837 + 360.98564736629*jd + 0.000387933*jc*jc - jc*jc*jc/38710000; 

if( GMST > 0.0 )	// circle goes round and round, adjust if < 0 or > 360 degrees
{
while( GMST > 360.0 )
GMST -= 360.0;
}
else
{
while( GMST < 0.0 )
GMST += 360.0;
}

return GMST;	// in degrees
}

function newLongitude()
{
var Prompt = "ENTER Complete Local Longitude in +/- DEGREES";
var Example = "Enter -117.5310333 for West Longitude 117° 31' 51.71988\"";
var Default = DefaultLongitude;
var RangeMin = -180;
var RangeMax = 180;
var Decimals = 7;	// 7 decimal places is 0.0000001 = 0.0004 arc seconds longitude is < 1/2" distance as the ant crawls

var InputValue = GetNumber( Prompt,Example,Default,RangeMin,RangeMax,Decimals );	// prompt for number value

if ( InputValue === false )
{
return;
}
else
{
UpdateLongitude(InputValue);	// update longitude displays
}
}

function GetNumber( Prompt,Example,Default,RangeMin,RangeMax,Decimals )
{
var InputValue = prompt(Prompt + ": RANGE = ( " + RangeMin + " to " + RangeMax + " )\nEXAMPLE: " + Example , Default );

if ( InputValue == null || InputValue == "" )
{
return false;	// prompt entry canceled or field returned blank so just ignore it
}
else if ( isNaN( InputValue ) == true )
{
alert("\"" +InputValue + "\" IS NOT A NUMBER: Please Input a Number...\nRANGE = ( " + RangeMin + " to " + RangeMax + " )");
return false;	// prompt entry was not a number so alert user and ignore it
}
else if ( InputValue < RangeMin || InputValue > RangeMax )
{
alert("INPUT OUT OF RANGE: ( " + InputValue + " ) \nRANGE = ( " + RangeMin + " to " + RangeMax + " )");
return false;	// prompt entry was a number but out of range so alert user and ignore it
}
else if ( Decimals == 0 )
{
InputValue = Math.floor(InputValue);	// no decimals returned
return InputValue;	// return it!	
}
else
var InRange = new Number( InputValue );	// prompt entry number within range so create number object
InputValue = InRange.toFixed( Decimals );	// use number object to round to requested number of decimals
return InputValue;	// return it!	
}

function UpdateLongitude(InputValue)
{
var longitude = parseFloat(InputValue);	// get decimal longitude from form input field

if ( longitude < 0.0 )	// Display Meridian value
{
document.clock.meridian.value = "West";	// negative = West
}
else if ( longitude > 0.0 )
{
document.clock.meridian.value = "East";	// positive = East
}
else
{
document.clock.meridian.value = "Prime";	// not E or W so must be Zero "Prime"
}

longitude = Math.abs(longitude);	// throw away negative sign
var degrees = Math.floor( longitude );	// save integer degrees without sign

longitude = longitude - degrees;	// get longitude minutes
longitude = longitude * 60;
var DecMinutes = longitude;	// save decimal minutes
var minutes = Math.floor( longitude );	// save integer minutes

longitude = longitude - minutes;	// get decimal longitude seconds
longitude = longitude * 60;
var seconds = longitude

var setDecimal = new Number( InputValue );	// restore longitude to number object
InputValue = setDecimal.toFixed(7);	// use number object to round to 7 decimals

var setDecimal = new Number( DecMinutes );	// save minutes with decimals as object
var DecMinutes = setDecimal.toFixed(6);	// use number object to round to 6 decimals

var setDecimal = new Number( seconds );	// save seconds with decimals as object
var seconds = setDecimal.toFixed(5);	// use number object to round seconds to 5 decimals

document.clock.longitude.value = InputValue + "°";	// update all longitude displays

document.clock.degrees.value = degrees + "°";	
document.clock.minutes.value = addZero( minutes ) + "\'";
document.clock.seconds.value = addZero( seconds ) + "\"";

document.clock.degrees2.value = document.clock.degrees.value
document.clock.dminutes.value = addZero( DecMinutes ) + "m";
document.clock.meridian2.value = document.clock.meridian.value 

}

function ShowAbout()
{
alert(" SIDEREAL CLOCK Javascript\n A Virtual Sidereal Clock for Windows Desktop.\n\nTo find your local \"STAR\" time, click on the set-up button set your local longitude value. \n\nEnter your longitude as decimal +/- DEGREES: ( -117.5310333° )\nEnter a negative number for WEST longitude and a positive number for EAST.\n\nACCURACY: Decimal Degrees rounded down to 7 decimal places.\n0.0000001° = 0.0004 ArcSeconds, which is less than 1/2 inch at the equator. \n\n Please click on the clock displays for more information...\n\nCopyright November 16, 2008 - James Melatis - webmaster@indigotide.com ")
}

function ShowLST()
{
alert(" SIDEREAL CLOCK Javascript\nLOCAL SIDEREAL TIME (LST) is the Right Ascension (RA) of the sky objects\ncurrently on your North/South Line. ( WHERE YOU ARE )\n\nIn other words, LOCAL STAR TIME.\n\nCopyright November 16, 2008 - James Melatis - webmaster@indigotide.com ")
}

function ShowGMST()
{
alert(" SIDEREAL CLOCK Javascript\nGMST is Greenwich Mean Sidereal Time, or the current \"STAR\" time at longitude zero. \n\nCopyright November 16, 2008 - James Melatis - webmaster@indigotide.com ")
}

function ShowGmstAngle()
{
alert(" SIDEREAL CLOCK Javascript\nGMST ANGLE is the same as Greenwich Mean Sidereal Time (GMST),\nexcept it is shown in DEGREES rather than time units. \n\nIt is the HOUR ANGLE of the sky objects currently on the North/South Line at longitude zero. \n\nOnce you know this in DEGREES, you can just add your local longitude DEGREES \nto find your local Hour Angle, then divide by 15 to get Local Sidereal Time.\n\nCopyright November 16, 2008 - James Melatis - webmaster@indigotide.com ")
}

function ShowAngle()
{
alert(" SIDEREAL CLOCK Javascript\nLST ANGLE is the same as Local Sidereal Time, except it is shown in DEGREES rather than time units. \n\nIt is the HOUR ANGLE of the sky objects currently on your North/South Line.\n\nCopyright November 16, 2008 - James Melatis - webmaster@indigotide.com ")
}

function ShowUTC()
{
alert(" SIDEREAL CLOCK Javascript\nUTC TIME is Universal Coordinated Time and is the same time everywhere.\nIt is also the same as what used to be called Greenwich Mean Time (GMT). \n\nUTC is the current time and date at longitude zero.\n\nWith local time, \"WHEN\" something will happen depends on \"WHERE\" you are.\nInstead, UTC provides a global frame of reference when talking about \"WHEN\" \nan event will take place.\n\nCopyright November 16, 2008 - James Melatis - webmaster@indigotide.com ")
}

function ShowLocal()
{
alert(" SIDEREAL CLOCK Javascript\nLOCAL TIME is just the 12-hour time and date where YOU are. \n\nCopyright November 16, 2008 - James Melatis - webmaster@indigotide.com ")
}

function ShowDay()
{
alert(" SIDEREAL CLOCK Javascript\nYEAR DAY is just the current day of the year where YOU are. \n\nCopyright November 16, 2008 - James Melatis - webmaster@indigotide.com ")
}

function getLST(location)
{
	DefaultLongitude = location;	// Put YOUR default local longitude here... AGAIN
	
	var long = parseFloat (DefaultLongitude);	// get longitude variable from current form INPUT text value
	// and convert to floating point number

	var now = new Date();	// get current date & time from computer clock

	var date = now.toLocaleString();	// format date as local full date and 12 hour clock
	var utc = now.toUTCString();	// format utc as UTC date & time

	var beg = new Date( now.getUTCFullYear() - 1, 11, 31 );	// get last day of previous year in milliseconds
	var day = Math.floor( ( now - beg ) / 86400000 );	// compute integer day of year (86400000 ms/day) 

	var mst = getGMST( now );	// get adjusted GMST in degrees for current system time 
	var mstAngle = mst;	// save for GMST Angle display

	// compute integer GMST hour angle deg min sec
	var gmstdeg = Math.floor( mstAngle );	// get integer GMST hour angle degrees right ascension of vernal equinox

	mstAngle = mstAngle - gmstdeg;	// get integer GMST hour angle minutes right ascension of vernal equinox
	mstAngle = mstAngle * 60;
	var gmstmin = Math.floor( mstAngle );

	mstAngle = mstAngle - gmstmin;	// get integer GMST hour angle seconds right ascension of vernal equinox
	mstAngle = mstAngle * 60;
	var gmstsec = Math.floor( mstAngle );

	var lst = mst + long;	// now we know GMST so just add local longitude offset

	if( lst > 0.0 )	// circle goes round and round, adjust LST if < 0 or > 360 degrees
	{
	while( lst > 360.0 )
	lst -= 360.0;
	}
	else
	{
	while( lst < 0.0 )
	lst += 360.0;
	}

	var ras = lst;	// save LST degrees right ascension for hour angle display

	lst = lst / 15.0;	// change LST from degrees to time units (15 deg/hour)
	mst = mst / 15.0;	// change MST from degrees to time units (15 deg/hour)

	// compute integer LST hour angle deg min sec
	var deg = Math.floor( ras );	// get integer hour angle degrees right ascension of vernal equinox

	ras = ras - deg;	// get integer hour angle minutes right ascension of vernal equinox
	ras = ras * 60;
	var min = Math.floor( ras );

	ras = ras - min;	// get integer hour angle seconds right ascension of vernal equinox
	ras = ras * 60;
	var sec = Math.floor( ras );

	// compute local sidereal time hour minute second
	hour = Math.floor( lst );	// get integer LST hour

	lst = lst - hour;	// get integer LST minute
	lst = lst * 60;
	minute = Math.floor( lst );

	lst = lst - minute;	//get integer LST second
	lst = lst * 60;
	second = Math.floor( lst ); 
	// compute GMST time hours minutes seconds
	hours = Math.floor( mst );	// get integer MST hours

	mst = mst - hours;	// get integer MST minutes
	mst = mst * 60;
	minutes = Math.floor( mst );

	mst = mst - minutes;	//get integer MST seconds
	mst = mst * 60;
	seconds = Math.floor( mst ); 
	
	
	return " " + addZero( hour ) + ":" + addZero( minute ) + ":" + addZero( second );
}

function getLST1()
{
	DefaultLongitude = -74.0060;	// Put YOUR default local longitude here... AGAIN
	
	var long = parseFloat (DefaultLongitude);	// get longitude variable from current form INPUT text value
	// and convert to floating point number

	var now = new Date();	// get current date & time from computer clock

	var date = now.toLocaleString();	// format date as local full date and 12 hour clock
	var utc = now.toUTCString();	// format utc as UTC date & time

	var beg = new Date( now.getUTCFullYear() - 1, 11, 31 );	// get last day of previous year in milliseconds
	var day = Math.floor( ( now - beg ) / 86400000 );	// compute integer day of year (86400000 ms/day) 

	var mst = getGMST( now );	// get adjusted GMST in degrees for current system time 
	var mstAngle = mst;	// save for GMST Angle display

	// compute integer GMST hour angle deg min sec
	var gmstdeg = Math.floor( mstAngle );	// get integer GMST hour angle degrees right ascension of vernal equinox

	mstAngle = mstAngle - gmstdeg;	// get integer GMST hour angle minutes right ascension of vernal equinox
	mstAngle = mstAngle * 60;
	var gmstmin = Math.floor( mstAngle );

	mstAngle = mstAngle - gmstmin;	// get integer GMST hour angle seconds right ascension of vernal equinox
	mstAngle = mstAngle * 60;
	var gmstsec = Math.floor( mstAngle );

	var lst = mst + long;	// now we know GMST so just add local longitude offset

	if( lst > 0.0 )	// circle goes round and round, adjust LST if < 0 or > 360 degrees
	{
	while( lst > 360.0 )
	lst -= 360.0;
	}
	else
	{
	while( lst < 0.0 )
	lst += 360.0;
	}

	var ras = lst;	// save LST degrees right ascension for hour angle display

	lst = lst / 15.0;	// change LST from degrees to time units (15 deg/hour)
	mst = mst / 15.0;	// change MST from degrees to time units (15 deg/hour)

	// compute integer LST hour angle deg min sec
	var deg = Math.floor( ras );	// get integer hour angle degrees right ascension of vernal equinox

	ras = ras - deg;	// get integer hour angle minutes right ascension of vernal equinox
	ras = ras * 60;
	var min = Math.floor( ras );

	ras = ras - min;	// get integer hour angle seconds right ascension of vernal equinox
	ras = ras * 60;
	var sec = Math.floor( ras );

	// compute local sidereal time hour minute second
	hour = Math.floor( lst );	// get integer LST hour

	lst = lst - hour;	// get integer LST minute
	lst = lst * 60;
	minute = Math.floor( lst );

	lst = lst - minute;	//get integer LST second
	lst = lst * 60;
	second = Math.floor( lst ); 
	// compute GMST time hours minutes seconds
	hours = Math.floor( mst );	// get integer MST hours

	mst = mst - hours;	// get integer MST minutes
	mst = mst * 60;
	minutes = Math.floor( mst );

	mst = mst - minutes;	//get integer MST seconds
	mst = mst * 60;
	seconds = Math.floor( mst ); 
	
	
	return " " + addZero( hour ) + " : " + addZero( minute ) + " : " + addZero( second );
}

function getLST2()
{
	DefaultLongitude = 28.0473;	// Put YOUR default local longitude here... AGAIN
	
	var long = parseFloat (DefaultLongitude);	// get longitude variable from current form INPUT text value
	// and convert to floating point number

	var now = new Date();	// get current date & time from computer clock

	var date = now.toLocaleString();	// format date as local full date and 12 hour clock
	var utc = now.toUTCString();	// format utc as UTC date & time

	var beg = new Date( now.getUTCFullYear() - 1, 11, 31 );	// get last day of previous year in milliseconds
	var day = Math.floor( ( now - beg ) / 86400000 );	// compute integer day of year (86400000 ms/day) 

	var mst = getGMST( now );	// get adjusted GMST in degrees for current system time 
	var mstAngle = mst;	// save for GMST Angle display

	// compute integer GMST hour angle deg min sec
	var gmstdeg = Math.floor( mstAngle );	// get integer GMST hour angle degrees right ascension of vernal equinox

	mstAngle = mstAngle - gmstdeg;	// get integer GMST hour angle minutes right ascension of vernal equinox
	mstAngle = mstAngle * 60;
	var gmstmin = Math.floor( mstAngle );

	mstAngle = mstAngle - gmstmin;	// get integer GMST hour angle seconds right ascension of vernal equinox
	mstAngle = mstAngle * 60;
	var gmstsec = Math.floor( mstAngle );

	var lst = mst + long;	// now we know GMST so just add local longitude offset

	if( lst > 0.0 )	// circle goes round and round, adjust LST if < 0 or > 360 degrees
	{
	while( lst > 360.0 )
	lst -= 360.0;
	}
	else
	{
	while( lst < 0.0 )
	lst += 360.0;
	}

	var ras = lst;	// save LST degrees right ascension for hour angle display

	lst = lst / 15.0;	// change LST from degrees to time units (15 deg/hour)
	mst = mst / 15.0;	// change MST from degrees to time units (15 deg/hour)

	// compute integer LST hour angle deg min sec
	var deg = Math.floor( ras );	// get integer hour angle degrees right ascension of vernal equinox

	ras = ras - deg;	// get integer hour angle minutes right ascension of vernal equinox
	ras = ras * 60;
	var min = Math.floor( ras );

	ras = ras - min;	// get integer hour angle seconds right ascension of vernal equinox
	ras = ras * 60;
	var sec = Math.floor( ras );

	// compute local sidereal time hour minute second
	hour = Math.floor( lst );	// get integer LST hour

	lst = lst - hour;	// get integer LST minute
	lst = lst * 60;
	minute = Math.floor( lst );

	lst = lst - minute;	//get integer LST second
	lst = lst * 60;
	second = Math.floor( lst ); 
	// compute GMST time hours minutes seconds
	hours = Math.floor( mst );	// get integer MST hours

	mst = mst - hours;	// get integer MST minutes
	mst = mst * 60;
	minutes = Math.floor( mst );

	mst = mst - minutes;	//get integer MST seconds
	mst = mst * 60;
	seconds = Math.floor( mst ); 
	
	
	return " " + addZero( hour ) + " : " + addZero( minute ) + " : " + addZero( second );
}

function getLST3()
{
	DefaultLongitude = 115.8605;	// Put YOUR default local longitude here... AGAIN
	
	var long = parseFloat (DefaultLongitude);	// get longitude variable from current form INPUT text value
	// and convert to floating point number

	var now = new Date();	// get current date & time from computer clock

	var date = now.toLocaleString();	// format date as local full date and 12 hour clock
	var utc = now.toUTCString();	// format utc as UTC date & time

	var beg = new Date( now.getUTCFullYear() - 1, 11, 31 );	// get last day of previous year in milliseconds
	var day = Math.floor( ( now - beg ) / 86400000 );	// compute integer day of year (86400000 ms/day) 

	var mst = getGMST( now );	// get adjusted GMST in degrees for current system time 
	var mstAngle = mst;	// save for GMST Angle display

	// compute integer GMST hour angle deg min sec
	var gmstdeg = Math.floor( mstAngle );	// get integer GMST hour angle degrees right ascension of vernal equinox

	mstAngle = mstAngle - gmstdeg;	// get integer GMST hour angle minutes right ascension of vernal equinox
	mstAngle = mstAngle * 60;
	var gmstmin = Math.floor( mstAngle );

	mstAngle = mstAngle - gmstmin;	// get integer GMST hour angle seconds right ascension of vernal equinox
	mstAngle = mstAngle * 60;
	var gmstsec = Math.floor( mstAngle );

	var lst = mst + long;	// now we know GMST so just add local longitude offset

	if( lst > 0.0 )	// circle goes round and round, adjust LST if < 0 or > 360 degrees
	{
	while( lst > 360.0 )
	lst -= 360.0;
	}
	else
	{
	while( lst < 0.0 )
	lst += 360.0;
	}

	var ras = lst;	// save LST degrees right ascension for hour angle display

	lst = lst / 15.0;	// change LST from degrees to time units (15 deg/hour)
	mst = mst / 15.0;	// change MST from degrees to time units (15 deg/hour)

	// compute integer LST hour angle deg min sec
	var deg = Math.floor( ras );	// get integer hour angle degrees right ascension of vernal equinox

	ras = ras - deg;	// get integer hour angle minutes right ascension of vernal equinox
	ras = ras * 60;
	var min = Math.floor( ras );

	ras = ras - min;	// get integer hour angle seconds right ascension of vernal equinox
	ras = ras * 60;
	var sec = Math.floor( ras );

	// compute local sidereal time hour minute second
	hour = Math.floor( lst );	// get integer LST hour

	lst = lst - hour;	// get integer LST minute
	lst = lst * 60;
	minute = Math.floor( lst );

	lst = lst - minute;	//get integer LST second
	lst = lst * 60;
	second = Math.floor( lst ); 
	// compute GMST time hours minutes seconds
	hours = Math.floor( mst );	// get integer MST hours

	mst = mst - hours;	// get integer MST minutes
	mst = mst * 60;
	minutes = Math.floor( mst );

	mst = mst - minutes;	//get integer MST seconds
	mst = mst * 60;
	seconds = Math.floor( mst ); 
	
	
	return " " + addZero( hour ) + " : " + addZero( minute ) + " : " + addZero( second );
}

function getLST4()
{
	DefaultLongitude = 151.2093;	// Put YOUR default local longitude here... AGAIN
	
	var long = parseFloat (DefaultLongitude);	// get longitude variable from current form INPUT text value
	// and convert to floating point number

	var now = new Date();	// get current date & time from computer clock

	var date = now.toLocaleString();	// format date as local full date and 12 hour clock
	var utc = now.toUTCString();	// format utc as UTC date & time

	var beg = new Date( now.getUTCFullYear() - 1, 11, 31 );	// get last day of previous year in milliseconds
	var day = Math.floor( ( now - beg ) / 86400000 );	// compute integer day of year (86400000 ms/day) 

	var mst = getGMST( now );	// get adjusted GMST in degrees for current system time 
	var mstAngle = mst;	// save for GMST Angle display

	// compute integer GMST hour angle deg min sec
	var gmstdeg = Math.floor( mstAngle );	// get integer GMST hour angle degrees right ascension of vernal equinox

	mstAngle = mstAngle - gmstdeg;	// get integer GMST hour angle minutes right ascension of vernal equinox
	mstAngle = mstAngle * 60;
	var gmstmin = Math.floor( mstAngle );

	mstAngle = mstAngle - gmstmin;	// get integer GMST hour angle seconds right ascension of vernal equinox
	mstAngle = mstAngle * 60;
	var gmstsec = Math.floor( mstAngle );

	var lst = mst + long;	// now we know GMST so just add local longitude offset

	if( lst > 0.0 )	// circle goes round and round, adjust LST if < 0 or > 360 degrees
	{
	while( lst > 360.0 )
	lst -= 360.0;
	}
	else
	{
	while( lst < 0.0 )
	lst += 360.0;
	}

	var ras = lst;	// save LST degrees right ascension for hour angle display

	lst = lst / 15.0;	// change LST from degrees to time units (15 deg/hour)
	mst = mst / 15.0;	// change MST from degrees to time units (15 deg/hour)

	// compute integer LST hour angle deg min sec
	var deg = Math.floor( ras );	// get integer hour angle degrees right ascension of vernal equinox

	ras = ras - deg;	// get integer hour angle minutes right ascension of vernal equinox
	ras = ras * 60;
	var min = Math.floor( ras );

	ras = ras - min;	// get integer hour angle seconds right ascension of vernal equinox
	ras = ras * 60;
	var sec = Math.floor( ras );

	// compute local sidereal time hour minute second
	hour = Math.floor( lst );	// get integer LST hour

	lst = lst - hour;	// get integer LST minute
	lst = lst * 60;
	minute = Math.floor( lst );

	lst = lst - minute;	//get integer LST second
	lst = lst * 60;
	second = Math.floor( lst ); 
	// compute GMST time hours minutes seconds
	hours = Math.floor( mst );	// get integer MST hours

	mst = mst - hours;	// get integer MST minutes
	mst = mst * 60;
	minutes = Math.floor( mst );

	mst = mst - minutes;	//get integer MST seconds
	mst = mst * 60;
	seconds = Math.floor( mst ); 
	
	
	return " " + addZero( hour ) + " : " + addZero( minute ) + " : " + addZero( second );
}

// End Script "sidereal.js"
// unhide -->
