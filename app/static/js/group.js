$(function()
{
	$(document).on("click", ".edit-description", function()
	{
		$(this).parent().html('<input class="input description-editor form-control" type="text" data-path="'+$(this).attr("data-path")+'" value="'+$(this).parent().text()+'" />');
		$(".description-editor").focus();
	});
	$(document).on("blur", ".description-editor", function()
	{
		console.log($(this).val());
		$.post("/group/"+$(this).attr("data-path")+"/modify", {
			description: $(this).val()
		},
		function(data)
		{
			console.log(data);
		}, "json");
		$(this).parent().html($(this).val()+'<span class="glyphicon glyphicon-pencil edit-description" data-path="'+$(this).attr("data-path")+'" aria-hidden="true"></span>');
	});
	$(document).on("keyup", ".description-editor", function(e)
	{
		if(e.which == 13) // Enter key
			$(this).blur();
	});
});

