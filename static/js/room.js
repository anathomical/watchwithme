_xSocket = {
	socket : "",
	chat_window : "",
	open : function(socket_uri) {
		_xSocket.chat_window = document.getElementById('chat-window');
		_xSocket.socket = new WebSocket(socket_uri);
		_xSocket.socket.onopen = function() { 
			console.log("Opened socket.  Sending auth info.");
			_xSocket.socket.send(JSON.stringify({
				'type': 'LOGIN',
				'user_email': _user_email,
				'user_token': _user_token,
			}));
		};
		_xSocket.socket.onmessage = _xSocket.handle_message;
		_xSocket.socket.onclose = function() { console.log("Closed socket."); };
	},
	handle_message : function(evt) {
		console.log(evt.data);
		var data = JSON.parse(evt.data);
		if (data.type == 'CHAT') {
			_xSocket.show_message(data.user, 'TIMESTAMP', data.data.message);
		}
		else if (data.type == 'PLAY') {
			_xVideo.start_playing();
		}
		else if (data.type == 'PAUSE') {
			_xVideo.pause_playing();
		}
        else if (data.type == 'SET_SOURCE') {
            _xVideo.set_video_source(data.data.message.source_url);
        }
	},
	show_message : function(user, timestamp, message) {
		var display_message = user + ':' + message;
		_xSocket.chat_window.innerHTML += '<p>'+display_message+'</p>';
		_xSocket.chat_window.scrollTop = _xSocket.chat_window.scrollHeight;
	},
	click_play : function() {
		_xSocket.socket.send(JSON.stringify({
			'type': 'PLAY',
		}));
	},
	click_pause : function() {
		_xSocket.socket.send(JSON.stringify({
			'type': 'PAUSE',
		}));
	},
}
_xVideo = {
	element : "",
	init : function() {
		_xVideo.element = document.getElementById('video-player');
		$(_xVideo.element).on('play',  function(evt) {
            _xSocket.click_play();

			console.log('playing');
		});
		$(_xVideo.element).on('pause', function(evt) {
            _xSocket.click_pause();
			console.log('pausing');
		});
	},
	start_playing : function() {
		_xVideo.element.play();
	},
	pause_playing : function() {
		_xVideo.element.pause();
	},
    set_video_source : function (source_url) {
        this.element.pause();
        $(this.element)
            .find('source')
            .attr('src', source_url);
        this.element.load();
        this.element.addEventListener('loadeddata', function() {
            _xSocket.socket.send(JSON.stringify({
                'type': 'CHAT',
                'message': 'Loaded video file'
            }));
        });
    }
}

var initSocketHandlers = function(location) {
	_xSocket.open(location);
	$("#socket_form").on('submit', function() {
		var input_element = $('#socket_input');
		_xSocket.socket.send(JSON.stringify({
			'type': 'CHAT',
			'message': input_element.val(),
		}));
		input_element.val('');
		return false;
	});

    $("#source_url_form").on('submit', function() {
        var new_source = $('#source_url_input').val();
        _xSocket.socket.send(JSON.stringify({
            'type': 'SET_SOURCE',
            'message': {
                'source_url': new_source,
            },
        }));
        return false;
    });

	$('#close_socket').on('click', function() {
		_xSocket.socket.close();
	});

	_xVideo.init();
}
