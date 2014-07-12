angular.module('app', ['ngResource']);

function getParameterByName(name) {
    name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
        results = regex.exec(location.search);
    return results == null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}

function CreatePage($scope, $resource) {
    $scope.name = "";
    $scope.save = "";
    $scope.conversations = "";
    $scope.createChat = function() {
	var oncreateresource = $resource('/new',{}, { post: {method:'POST'}});
	var data = oncreateresource.post({
	    "name": $scope.name,
	    "save": $scope.save,
	    "conversations": $scope.conversations
	    }
					)
    }
}

function MainPage($scope,$resource) {
    $scope.token = "";
    $scope.id = "";
    $scope.author = "";
    $scope.connected = 1;
    $scope.title = "Cloud Chat";
    $scope.message = "";
    $scope.messages = [];

    $scope.onOpened = function() {
	var onopenresource = $resource('/opened',{},{ post: {method:'POST'}});
	var data = onopenresource.post({
	    'id': $scope.id});
    };

    $scope.onClosed = function() {
	var onopenresource = $resource('/closed',{},{ post: {method:'POST'}});
	var data = onopenresource.post({
	    'id': $scope.id});
    };


    $scope.onMessage = function(m) {
        data = JSON.parse(m.data);
	console.debug(data);
	messages = data.message
	$scope.$apply(function () {
	    $scope.connected = data.clients;
	    $scope.title = data.name;
	    for (i in messages){
		$scope.messages.unshift({"author": messages[i].author,
					 "when": messages[i].when,
					 "text": messages[i].text}
			    );
		}
	}
		     );
    };

    $scope.connect = function(){
	$scope.channel = new goog.appengine.Channel($scope.token);
	$scope.handler = {
	    'onopen': $scope.onOpened,
	    'onmessage': $scope.onMessage,
	    'onerror': function() {},
	    'onclose': $scope.onClosed,
	}
	$scope.socket = $scope.channel.open($scope.handler);
	$scope.socket.onopen = $scope.onOpened;
	$scope.socket.onmessage = $scope.onMessage;
    }

    var tokenresource = $resource("/token?key=:q");
    var data = tokenresource.get({q:getParameterByName('key')}, function(){
    	$scope.token = data.token;
	$scope.id = data.id;
	$scope.connect();
    });

    $scope.sendMessage = function(){
	var messageresource = $resource('/message',{},{ post: {method:'POST'}});
	var data = messageresource.post({
	    'id': $scope.id,
	    'author': $scope.author,
	    'text': $scope.message
	}
				       );
	$scope.message="";
    };
    
};
