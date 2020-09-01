function reloadradiosky() {
 var frameHolder=document.getElementById('radiosky');
frameHolder.src = frameHolder.src;
  // document.getElementById("radiosky").location.reload(true);
}
window.onload = setInterval(reloadradiosky, 30000);
