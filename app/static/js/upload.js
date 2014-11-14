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
var isRemoteFile = false;
var existingGroups = [];

window.onpopstate = function(event) {
	// FIXME: Mobile Safari fires window.onpopstate even on first page load
	if(event.state == null)
		return;
	browserCurrPath = event.state;
	browse(event.state);
	console.log("location: " + document.location + ", state: " + JSON.stringify(event.state));
};

function browse(path)
{
	$("#browser-currdir").text(browserCurrPath);
	$.getJSON("/api/browse?path="+path, function(data)
	{
		console.log(data);
		$(".browser-alert").remove();
		$(".browser-element").remove();
		if(data.result)
		{
			$("#browser-tbody").append("<tr class=\"browser-element browser-parent-dir\"><td>D</td><td>..</td><td></td></tr>");
			$.each(data.data.directories, function(_, fn)
			{
				$("#browser-tbody").append("<tr class=\"browser-element\"><td>D</td><td class=\"browser-directory\">"+fn+"</td><td><button class=\"depot-box browser-upload-all\" style=\"padding: 1px;\" type=\"button\">Upload all</button></td></tr>");
			});
			$.each(data.data.files, function(_, fn)
			{
				$("#browser-tbody").append("<tr class=\"browser-element\"><td>F</td><td class=\"browser-file\">"+fn.name+"</td><td>"+fn.size+"</td></tr>");
			});
		}
		else
		{
			$("#browser-tbody").append("<tr><th colspan=\"3\" class=\"browser-alert\">Error: " + data.message + "</th></tr>");
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

        	isRemoteFile = false;

		$("#filenameInput").css({ 'text-align': 'left' });
		$(".uploadProgress").removeClass("progress-bar-danger");
        
		var filename = $(this).val().replace(/\\/g, '/');
		filename = filename.substr(filename.lastIndexOf('/') + 1);
        
		$("#filenameInput").val(filename);
	});
   	$(document).on("click", ".uploadButton", function()
	{
		if($("#filenameInput").val())
			$("#uploadForm").submit();
	});
	$("#uploadForm").submit(function (e)
	{
		if (isRemoteFile)
			upload(browserCurrPath+$("#filenameInput").val());
		else
			upload();
		e.preventDefault();
	});
	$("#open-browser").click(function()
	{
		if($("#browser").is(":hidden"))
		{
			$(this).text("Close remote file browser");
			$("#browser").slideDown("fast");
			$("#browser-tbody").append("<tr><th colspan=\"3\" class=\"browser-alert\">Loading</th></tr>");
			history.pushState("/", "", "#/");
			browse("/");
		}
		else
		{
			$(this).text("Open remote file browser");
			$("#browser").hide();
		}
	});

	$("#create-random-group").click(function()
	{
		$.post("/groups/create", undefined, function(data)
		{
			$("#group-name").val(data.path);
		}, 'json');
		$(this).attr("disabled", "disabled");
	});
	$(document).on("click", ".browser-directory", function()
	{
		browserCurrPath = browserCurrPath + $(this).text() + "/";
		history.pushState(browserCurrPath, "", "#"+browserCurrPath);
		browse(browserCurrPath);
	});
	$(document).on("click", ".browser-parent-dir", function()
	{
		$("#filenameInput").val("");
		browserCurrPath = browserCurrPath.split("/").filter(function(a){return a.length != 0;});
		if(!browserCurrPath)
		{
			return;
		}
		currPathList = browserCurrPath.splice(0, browserCurrPath.length-1);
		console.log(currPathList);
		browserCurrPath = "/" + currPathList.join("/");
		if(currPathList.length != 0)
			browserCurrPath = browserCurrPath + "/";
		history.pushState(browserCurrPath, "", "#"+browserCurrPath);
		browse(browserCurrPath);
	});
	$(document).on("click", ".browser-file", function()
	{
		$(".browser-upload-button").remove();
		$("#filenameInput").val($(this).text());
		$(this).parent().after("<tr class=\"browser-element browser-upload-button\"><th colspan=\"3\"><button class=\"depot-box uploadButton\" type=\"button\" style=\"width: 100%;\">Upload</button></th></tr>");
		isRemoteFile = true;
	});
	$(document).on("click", ".browser-upload-all", function()
	{
		var dir = $(this).parent().parent().children(".browser-directory").text();
		$.getJSON("/api/browse?path="+browserCurrPath+dir, function(data)
		{
			if(data.data.files.length > 0)
			{
				if(confirm("This directory has "+data.data.files.length+" of files. Are you sure?"))
				{
					$.each(data.data.files, function(_, fi)
					{
						console.log(fi.name);
						isRemoteFile = true;
						$("#filenameInput").val(fi.name);
						upload(browserCurrPath+dir+"/"+fi.name);
					});
				}
			}
			else
			{
				alert("This directory doesn't contain any files");
			}
		});
	});

	$(document).on("click", ".link-container", function()
	{
		$(this).select();
	});

	var dropZone = document.getElementById('filenameInput');
	dropZone.addEventListener('dragover', handleDragOver, false);
	dropZone.addEventListener('drop', handleFileSelect, false);
});

function timeUnitConverter(unit, value)
{
	var t = {"s": 1, "m": 60, "h": 3600, "d": 86400};
	return value*t[unit];
}

function upload(path)
{
	var formData = new FormData($("#uploadForm")[0]);
	if(isRemoteFile)
	{
		formData.append("local", 1);
		console.log(path);
		formData.append("path", path);
	}
	var id = makeid();
	
	// Convert #expires_in to seconds
	if($("#expires_in").val() !== "")
	{
		console.log(timeUnitConverter($("#expires_in").val(), $("#expires_in_unit").val()));
		formData.append("expires_in", timeUnitConverter($("#expires_in_unit").val(), $("#expires_in").val()));
	}

	var filename = $("#filenameInput").val();
	var fileext = filename.split('.').pop();

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
			var item = $("<li class=\"list-group-item upload-list-item list_"+id+"\"><a class=\"a_"+id+"\">"+filename+"</a> </li>");
			var progbar = $('<div class="progress"><div id="progress_'+id+'" class="progress-bar" role="progressbar" style="width: 0%;"></div></div>');
			item.append(progbar);
			$("#uploadList").prepend(item);
		},
		complete: function () {
	        },
		success: function(data)
		{
			var data = JSON.parse(data);
			console.log(data);
			var item = $(".list_"+id);
			if(data.result)
			{
				var fullurl = location.origin + "/" + data.path;
				var link = "<a href=\"" + fullurl + "\">"+fullurl+"</a>";
				var s = " " + link;
				s += "<div class=\"row\">";
				s += "<div class=\"col-xs-12 col-sm-6\" style=\"display: inline-block\"><h4>Information</h4><input type=\"text\" value=\""+fullurl+"\" class=\"form-control link-container\" /></div>";
				s += "<div class=\"col-xs-12 col-sm-6\" style=\"display: inline-block\"><h4>Direct download</h4><input type=\"text\" value=\""+fullurl+"."+fileext+"\" class=\"form-control link-container\" /></div>";
				s += "</div>";
				$(".a_"+id).after(s);
				$("#prgoress_"+id).css({ width: "100%" });
			}
			else
			{
				$(".a_"+id).after(" - <span style=\"color: red\">Error: "+data.message+"</span>");
			}
		},
        	error: function (xhr, ajaxOptions, thrownError) {
	        },
		data: formData,
        	cache: false,
		contentType: false,
		processData: false
	});
	$("#filenameInput").val("");
	isRemoteFile = false;
}
