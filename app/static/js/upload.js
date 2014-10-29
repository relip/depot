function handleFileSelect(evt) {
	evt.stopPropagation();
	evt.preventDefault();
	$(".fileInput")[0].files = evt.dataTransfer.files;
}

function handleDragOver(evt) {
	evt.stopPropagation();
	evt.preventDefault();
	evt.dataTransfer.dropEffect = 'copy'; // Explicitly show this is a copy.
}

function makeid()
{
    var text = "";
    var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

    for( var i=0; i < 5; i++ )
        text += possible.charAt(Math.floor(Math.random() * possible.length));

    return text;
}

var browserCurrPath = "/";
var isLocalFile = false;

function browse(path)
{
	$("#depot-browser-currdir").text(browserCurrPath);
	$.getJSON("/api/browse?path="+path, function(data)
	{
		console.log(data);
		$(".depot-browser-alert").remove();
		$(".depot-browser-element").remove();
		$("#depot-browser-tbody").append("<tr class=\"depot-browser-element depot-browser-parent-dir\"><td>D</td><td>..</td><td></td></tr>");
		if(data.result)
		{
			$.each(data.data.directories, function(_, fn)
			{
				$("#depot-browser-tbody").append("<tr class=\"depot-browser-element\"><td>D</td><td class=\"depot-browser-directory\">"+fn+"</td><td></td></tr>");
			});
			$.each(data.data.files, function(_, fn)
			{
				$("#depot-browser-tbody").append("<tr class=\"depot-browser-element\"><td>F</td><td class=\"depot-browser-file\">"+fn.name+"</td><td>"+fn.size+"</td></tr>");
			});
		}
		else
		{
			$("#depot-browser-tbody").append("<tr><th colspan=\"3\" class=\"depot-browser-alert\">Error: " + data.message + "</th></tr>");
		}
	});
}

$(function () {
	$(".selectButton").click(function() {
		$(".fileInput").click();
	});
	$("#filenameInput").click(function()
	{
		$(".fileInput").click();
	});

	$(".fileInput").change(function()
	{
		if ($(this).val().length <= 0) { return; }

        	isLocalFile = False;

		$("#filenameInput").css({ 'text-align': 'left' });
		$(".uploadProgress").removeClass("progress-bar-danger");
        
		var filename = $(this).val().replace(/\\/g, '/');
		filename = filename.substr(filename.lastIndexOf('/') + 1);
        
		$("#filenameInput").val(filename);
	});
   	$(".uploadButton").click(function()
	{
		$(".uploadForm").submit();	
	});
	$(".uploadForm").submit(function (e) {
		upload();
		e.preventDefault();
	});
	$("#depot-browse-button").click(function()
	{
		if($("#depot-browser").is(":hidden"))
		{
			$("#depot-browser").slideDown("slow");
			$("#depot-browser-tbody").append("<tr><th colspan=\"3\" class=\"depot-browser-alert\">Loading</th></tr>");
			browse("/");
		}
		else
		{
			$("#depot-browser").hide();
		}
	});
	$(document).on("click", ".depot-browser-directory", function()
	{
		browserCurrPath = browserCurrPath + $(this).text() + "/";
		browse(browserCurrPath);
	});
	$(document).on("click", ".depot-browser-parent-dir", function()
	{
		browserCurrPath = browserCurrPath.split("/").filter(function(a){return a.length != 0;});
		if(!browserCurrPath)
		{
			return;
		}
		currPathList = browserCurrPath.splice(0, browserCurrPath.length-1);
		browserCurrPath = "/" + currPathList.join("/");
		if(!currPathList)
			browserCurrPath = browserCurrPath + "/";
		browse(browserCurrPath);
	});
	$(document).on("click", ".depot-browser-file", function()
	{
		$("#filenameInput").val($(this).text());
		isLocalFile = true;
	});

	var dropZone = document.getElementById('filenameInput');
	dropZone.addEventListener('dragover', handleDragOver, false);
	dropZone.addEventListener('drop', handleFileSelect, false);
});

function showAlert(id, msg) {
    $("#" + id + " > #alertText").text(msg);
    
    $("#" + id).animate({ bottom: 0 }, 500);
    setTimeout(function () {
        $("#" + id).animate({ bottom: -70 }, 300);
    }, 2000);
}

function uploadLocalFile()
{
}

function upload()
{
	if(isLocalFile)
	{
		var formData = new FormData();
		formData.append("local", 1);
		console.log(browserCurrPath+$("#filenameInput").val());
		formData.append("path", browserCurrPath+$("#filenameInput").val());
	}
	else
		var formData = new FormData($(".uploadForm")[0]);
	var id = makeid();

	$.ajax({
		url: "/upload",
		type: "POST",
		xhr: function()
		{
			var xhr = $.ajaxSettings.xhr();
			if (xhr.upload)
			{
				xhr.upload.addEventListener('progress', function(event)
				{
					var value = (event.loaded / event.total) * 100;  
					$("#progress_"+id).css({ width: value + "%" });
				}, false);
			}
            
			return xhr;
		},
		beforeSend: function ()
		{
			var item = $("<li class=\"list-group-item upload-list-item list_"+id+"\"><a class=\"a_"+id+"\">"+$("#filenameInput").val()+"</a> </li>");
			var progbar = $('<div class="progress"><div id="progress_'+id+'" class="progress-bar" role="progressbar" style="width: 0%;"></div></div>');
			item.append(progbar);
			$("#uploadList").append(item);
		},
		complete: function () {
	        },
		success: function(data)
		{
			var data = JSON.parse(data);
			var item = $(".list_"+id);
			var fullurl = location.origin + "/" + data.path;
			var link = "<a href=\"" + fullurl + "\">"+fullurl+"</a>";
			$(".a_"+id).after(" - "+link);
			$("#prgoress_"+id).css({ width: "100%" });
		},
        	error: function (xhr, ajaxOptions, thrownError) {
	        },
		data: formData,
        	cache: false,
		contentType: false,
		processData: false
    });
}
