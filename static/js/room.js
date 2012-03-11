_xSocket = {
	socket : "",
	open : function() {
		_xSocket.socket = new WebSocket("ws://ec2-107-20-131-22.compute-1.amazonaws.com/room/1/socket");
		_xSocket.socket.onopen = function() { console.log("Opened socket."); };
		_xSocket.socket.onmessage = function(evt) { console.log(evt); };
		_xSocket.socket.onclose = function() { console.log("Closed socket."); };
	}
}
$(document).ready( function() {
	_xSocket.open();
	$("#socket_form").on('submit', function() {
		var input_element = $('#socket_input');
		_xSocket.socket.send(input_element.val());
		input_element.val('');
				
		return false;
	});
		$('#close_socket').on('click', function() {
		_xSocket.socket.close();
	});
});
