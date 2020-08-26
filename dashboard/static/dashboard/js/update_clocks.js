const clocks = document.getElementsByClassName("clock_sidereal");
const dates = document.getElementsByClassName("date");

function updateClocks() {
  <!-- Longitudes of observatories -->
  var points = [22.13]
  var i = 0;
  for (let clock of clocks) {
    clock.textContent = getLST(points[i]);
    i++;
  }
}

function updateDates() {
  for (let date of dates) {
    let datezone = date.dataset.timezone;
    let datestr = new Date().toLocaleTimeString("en-GB", {
      day:'numeric',
      month:'long',
      timeZone: datezone
    });
    date.textContent = datestr
  }
}

// Update every second:

setInterval(updateClocks, 1000);
updateClocks();
setInterval(updateDates, 1000);
updateDates();

// Local time
(function (d, DEADLINE, serverTime) {
  var timeDelta = serverTime - (Date.now() + 3600000) / 1000,
    interval;

  var UI = {
    days: d.getElementById('days'),
    hours: d.getElementById('hours'),
    minutes: d.getElementById('minutes'),
    seconds: d.getElementById('seconds')
  };

  function getTimeRemaining() {
    var dt = DEADLINE - (Date.now() + 3600000) / 1000 - timeDelta;
    return {
      total: dt,
      days: Math.floor(dt / (60 * 60 * 24)),
      hours: Math.floor((dt / (60 * 60)) % 24),
      minutes: Math.floor((dt / 60) % 60),
      seconds: Math.floor(dt % 60)
    };
  }

  function updateClock() {
    var t = getTimeRemaining();
    if (t.total < 0) {
      clearInterval(interval);
      return;
    }
    UI.days.innerHTML = t.days;
    UI.hours.innerHTML = ('0' + t.hours).slice(-2);
    UI.minutes.innerHTML = ('0' + t.minutes).slice(-2);
    UI.seconds.innerHTML = ('0' + t.seconds).slice(-2);
  }

  d.documentElement.className = 'js';
  interval = setInterval(updateClock, 1000);
  updateClock();

})(document, 1580346060, (Date.now()) / 1000);

// calculate the current JD
(function (d, serverTime) {
  var timeDelta = serverTime - (Date.now() + 3600000) / 1000,
    interval;

  var UI = {
    days: d.getElementById('julian_date'),
  };

  function getTimeRemaining() {
    var dt = (Date.now() + 3600000) / 1000 - timeDelta;
    return {
      total: dt,
      days: Math.floor(dt / (60 * 60 * 24) + 2440587.5),
    };
  }

  function updateClock() {
    var t = getTimeRemaining();
    if (t.total < 0) {
      clearInterval(interval);
      return;
    }

    UI.days.innerHTML = t.days;
  }

  d.documentElement.className = 'js';
  interval = setInterval(updateClock, 1000);
  updateClock();

})(document, (Date.now()) / 1000);

// python retirement
(function (d, DEADLINE, serverTime) {
  var timeDelta = serverTime - (Date.now() + 3600000) / 1000,
    interval;

  var UI = {
    days: d.getElementById('pydays'),
    hours: d.getElementById('pyhours'),
    minutes: d.getElementById('pyminutes'),
    seconds: d.getElementById('pyseconds')
  };

  function getTimeRemaining() {
    var dt = DEADLINE - (Date.now() + 3600000) / 1000 - timeDelta;
    return {
      total: dt,
      days: Math.floor(dt / (60 * 60 * 24)),
      hours: Math.floor((dt / (60 * 60)) % 24),
      minutes: Math.floor((dt / 60) % 60),
      seconds: Math.floor(dt % 60)
    };
  }

  function updateClock() {
    var t = getTimeRemaining();
    if (t.total < 0) {
      clearInterval(interval);
      return;
    }
    UI.days.innerHTML = t.days;
    UI.hours.innerHTML = ('0' + t.hours).slice(-2);
    UI.minutes.innerHTML = ('0' + t.minutes).slice(-2);
    UI.seconds.innerHTML = ('0' + t.seconds).slice(-2);
  }

  d.documentElement.className = 'js';
  interval = setInterval(updateClock, 1000);
  updateClock();

})(document, 1577836800, (Date.now()) / 1000);
