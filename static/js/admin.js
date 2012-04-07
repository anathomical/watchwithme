$(function(){
	$('form.user_roles').on('submit', function(evt) {
		evt.preventDefault();
		var data = {}
		var inputs = $(evt.target).find('input');
                for(var i = 0; i < inputs.length; i++){
			if(inputs[i].name){
				if(inputs[i].type == "checkbox")
					data[inputs[i].name] = inputs[i].checked;
				else
					data[inputs[i].name] = inputs[i].value;
			}
		}
		$.post('/admin/update_user_roles', data, function(ret){
			console.log('post complete');
			console.log(ret);
		});
		return false;
	});
});
