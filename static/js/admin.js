$(function(){
	$('form.ajax-intercept-form').on('submit', function(evt) {
		evt.preventDefault();
		var form = $(evt.target);
		var data = {};
		var inputs = form.find('input');
                for(var i = 0; i < inputs.length; i++){
			if(inputs[i].name){
				if(inputs[i].type == "checkbox")
					data[inputs[i].name] = inputs[i].checked;
				else
					data[inputs[i].name] = inputs[i].value;
			}
		}
		$.ajax({
			'type': form.attr('method'),
			'url': form.attr('action'),
			'data':  data,
			'success': function(ret){
				console.log(ret);
			}
		});
		return false;
	});
});
