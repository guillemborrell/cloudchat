angular.module('app', ['ngResource']);

function MainPage($scope,$resource) {
    $scope.token = "";
    $scope.id = "";
    $scope.author = "";
    $scope.message = "";
    $scope.messages = [];

    $scope.onOpened = function() {
	var onopenresource = $resource('/opened',{},{ post: {method:'POST'}});
	var data = onopenresource.post({
	    'id': $scope.id});
    };

    $scope.onMessage = function(m) {
        message = JSON.parse(m.data);
	$scope.$apply(function () {
	    $scope.messages.unshift({"author": message.author,
				     "when": message.when,
				     "text": message.text}
			    );
	}
		     );
    };

    $scope.connect = function(){
	$scope.channel = new goog.appengine.Channel($scope.token);
	$scope.handler = {
	    'onopen': $scope.onOpened,
	    'onmessage': $scope.onMessage,
	    'onerror': function() {},
	    'onclose': function() {},
	}
	$scope.socket = $scope.channel.open($scope.handler);
	$scope.socket.onopen = $scope.onOpened;
	$scope.socket.onmessage = $scope.onMessage;
    }

    var tokenresource = $resource("/token:q");
    var data = tokenresource.get({q:""}, function(){
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
