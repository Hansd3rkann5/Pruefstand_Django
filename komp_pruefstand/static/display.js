var file = document.getElementById("fileDropBox");
var start = document.getElementById("start")

file.addEventListener("dragstart", function(evt){
evt.dataTransfer.setData("DownloadURL",fileDetails);
},false);

