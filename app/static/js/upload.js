/*
 * upload.js: contains file upload related functions
 * See LICENSE
 */

// -------------------------------------------------- DRAG AND DROP

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

// -------------------------------------------------- REMOTE FILE BROWSER

var browserCurrPath = [];

window.onpopstate = function(event) {
	// FIXME: Mobile Safari fires window.onpopstate even on first page load
	if(event.state == null)
		return;
	browserCurrPath = event.state.split("/").filter(function(a){return a.length != 0;});
};

// http://stackoverflow.com/a/20463021/1398994
function convertFileSize(a,b,c,d,e){
	return (b=Math,c=b.log,d=1024,e=c(a)/c(d)|0,a/b.pow(d,e)).toFixed(2)
	+' '+(e?'KMGTPEZY'[--e]+'iB':'B')
}

function getCurrentPath()
{
	var res = "/"+browserCurrPath.join("/");
	if(browserCurrPath.length)
		res += "/";
	return res;
}

function openBrowser()
{
	if($("#browser").is(":hidden"))
	{
		$("#open-browser").text("Close remote file browser");
		$("#browser").slideDown("fast");
		$("#browser-tbody").append("<tr><th colspan=\"3\" class=\"browser-alert\">Loading</th></tr>");
		history.pushState(getCurrentPath(), document.title, "#"+getCurrentPath());
		browse();
	}
	else
	{
		history.pushState("", document.title, window.location.pathname+window.location.search);
		$("#open-browser").text("Open remote file browser");
		$("#browser").hide();
	}
}

function browse()
{
	$("#browser-currdir").text(getCurrentPath());
	$.getJSON("/api/browse?path="+getCurrentPath(), function(data)
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
				$("#browser-tbody").append("<tr class=\"browser-element\"><td>F</td><td class=\"browser-file\">"+fn.name+"</td><td style=\"text-align: right\">"+convertFileSize(fn.size)+"</td></tr>");
			});
		}
		else
		{
			$("#browser-tbody").append("<tr><th colspan=\"3\" class=\"browser-alert\">Error: " + data.message + "</th></tr>");
		}
	});
}

// -------------------------------------------------- XHR

function timeUnitConverter(unit, value)
{
	var t = {"s": 1, "m": 60, "h": 3600, "d": 86400};
	return value*t[unit];
}

function makeid()
{
	var text = "";
	var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

	for( var i=0; i < 5; i++ )
		text += possible.charAt(Math.floor(Math.random() * possible.length));

	return text;
}

function uploadLocal(fileobj)
{
	var formData = new FormData($("#uploadForm")[0]);
	formData.append("file", fileobj);

	upload(fileobj.name, formData);

	$("#filenameInput").val("");
}

function uploadRemote(filename, remotePath)
{
	var formData = new FormData($("#uploadForm")[0]);

	formData.append("local", 1);
	formData.append("path", remotePath+"/"+filename);

	upload(filename, formData);
}

function upload(filename, formData)
{
	if($("#group-name").val())
	{
		$.post("/groups/create", {group_path: $("#group-name").val()}, function(data)
		{
			uploadWithoutGroupCreation(filename, formData);
		}, "json");
	}
	else
		uploadWithoutGroupCreation(filename, formData);
}

function uploadWithoutGroupCreation(filename, formData)
{
	var id = makeid();
	
	// Convert #expires_in to seconds
	if($("#expires_in").val() !== "")
	{
		console.log(timeUnitConverter($("#expires_in").val(), $("#expires_in_unit").val()));
		formData.append("expires_in", timeUnitConverter($("#expires_in_unit").val(), $("#expires_in").val()));
	}

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
			$(".fileInput").replaceWith($(".fileInput").val("").clone(true));
		},
        	error: function (xhr, ajaxOptions, thrownError) {
	        },
		data: formData,
        	cache: false,
		contentType: false,
		processData: false
	});
}

// -------------------------------------------------- EVENT LISTENERS

$(function () {
	$(".selectButton").click(function() {
		$(".fileInput").click();
	});

	$("#filenameInput").click(function()
	{
		$(".fileInput").click();
	});

	$("#upload-instant-form").click(function()
	{
		$(".fileInput").click();
	});

	$(".fileInput").change(function()
	{
		if ($(this).val().length <= 0) { return; }
 
		var filenames = [];
		$.each($(this).prop("files"), function(i, fo)
		{
			console.log(fo);
			var tempfn = fo.name.replace(/\\/g, '/');
			tempfn = tempfn.substr(tempfn.lastIndexOf('/') + 1);
			filenames.push(tempfn);
		});

		if ($(this).attr("class").indexOf("instant") > -1)
		{
			$("#filenameInput").text(filenames.join(", "));
			$(".uploadButton").show();
		}
		else
		{
			$("#filenameInput").css({ 'text-align': 'left' });
			$("#filenameInput").val(filenames.join(", "));
		}
	});

   	$(document).on("click", ".uploadButton", function()
	{
		if($(".fileInput").prop("files").length > 0)
			$("#uploadForm").submit();
	});
	$("#uploadForm").submit(function (e)
	{
		if($(".fileInput").prop("files").length > 1)
		{
			if(!confirm("Upload "+$(".fileInput").prop("files").length+" files?"))
			{
				return;
			}
		}

		$.each($(".fileInput").prop("files"), function(i, fo)
		{
			uploadLocal(fo);
		});
		e.preventDefault();
	});
	$("#open-browser").click(openBrowser);

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
		browserCurrPath.push($(this).text());
		history.pushState(getCurrentPath(), document.title, "#"+getCurrentPath());
		browse();
	});
	$(document).on("click", ".browser-parent-dir", function()
	{
		$("#filenameInput").val("");
		if(!browserCurrPath.length)
		{
			return;
		}
		browserCurrPath.pop()
		history.pushState(getCurrentPath(), document.title, "#"+getCurrentPath());
		browse()
	});
	$(document).on("click", ".browser-file", function()
	{
		$(".browser-upload-button").remove();
		$(this).parent().after("<tr class=\"browser-element browser-upload-button\"><th colspan=\"3\"><button class=\"depot-box browser-upload\" type=\"button\" style=\"width: 100%;\">Upload</button></th></tr>");
	});
	$(document).on("click", ".browser-upload-button", function()
	{
		uploadRemote($(this).prev().children(".browser-file").text(), getCurrentPath());
	});
	$(document).on("click", ".browser-upload-all", function()
	{
		var dir = $(this).parent().parent().children(".browser-directory").text();
		$.getJSON("/api/browse?path="+getCurrentPath()+dir, function(data)
		{
			if(data.data.files.length > 0)
			{
				if(confirm("This directory has "+data.data.files.length+" of files. Are you sure?"))
				{
					$.each(data.data.files, function(_, fi)
					{
						console.log(fi.name);
						uploadRemote(fi.name, getCurrentPath()+dir);
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

	$(window).bind('hashchange', function () {
		var hash = window.location.hash.substring(1);
		console.log(hash);
		browserCurrPath = hash.split("/").filter(function(a){return a.length != 0;});
		browse();
	});

	var dropZone = document.getElementById('filenameInput');
	dropZone.addEventListener('dragover', handleDragOver, false);
	dropZone.addEventListener('drop', handleFileSelect, false);

	if(window.location.hash)
	{
		var hash = window.location.hash.substring(1);
		browserCurrPath = hash.split("/").filter(function(a){return a.length != 0;});
		openBrowser();
	}
});

