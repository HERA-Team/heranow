function reloadradiosky() {
 var frameHolder=document.getElementById('radiosky');
frameHolder.src = frameHolder.src;
}
setInterval(reloadradiosky, 30000);
