/**
 * @name		Shuffle Letters
 * @author		Martin Angelov
 * @version 	1.0
 * @url			http://tutorialzine.com/2011/09/shuffle-letters-effect-jquery/
 * @license		MIT License
 */

 // Modified by Dustin Fast, where noted, to give a more random shuffle 
 // appearance when shuffling mostly numeric strings. Also to shuffle in-place,
 // rather than starting from an empty string.

// Added by DF, 9/2/2018, 
pool = 'abcdefghijklmnopqrstuvwxyz0123456789,.?/\\(^)![]{}*&^%$#'
var arr = pool.split('');

(function($){
	
	$.fn.shuffleLetters = function(prop){
		
		var options = $.extend({
			"step"		: 8,			// How many times should the letters be changed
			"fps"		: 25,			// Frames Per Second
			"text"		: "", 			// Use this text instead of the contents
			"callback"	: function(){}	// Run once the animation is complete
		},prop)
		
		return this.each(function(){
			
			var el = $(this),
				str = "";

			// var el_width = el.width();
			// console.log(el_width);


			// Preventing parallel animations using a flag;

			if(el.data('animated')){
				return true;
			}
			
			el.data('animated',true);
			
			
			if(options.text) {
				str = options.text.split('');
			}
			else {
				str = el.text().split('');
			}
			
			// The types array holds the type for each character;
			// Letters holds the positions of non-space characters;
			
			var letters = [];

			// Looping through all the chars of the string
			
			for(var i=0;i<str.length;i++){
				
				// Removed by DF, 9/2/2018
				// var ch = str[i];
				
				// if(ch == " "){
				// 	types[i] = "space";
				// 	continue;
				// }
				// else if(/[a-z]/.test(ch)){
				// 	types[i] = "lowerLetter";
				// }
				// else if(/[A-Z]/.test(ch)){
				// 	types[i] = "upperLetter";
				// }
				// else {
				// 	types[i] = "symbol";
				// }
				
				letters.push(i);
			}
			
			// el.html("");	  // Removed by DF, 9/2/2018		

			// Self executing named function expression:
			
			(function shuffle(start){
			
				// This code is run options.fps times per second
				// and updates the contents of the page element
					
				var i,
					len = letters.length, 
					strCopy = str.slice(0);	// Fresh copy of the string
					
				if(start>len){
					
					// The animation is complete. Updating the
					// flag and triggering the callback;
					
					el.data('animated',false);
					options.callback(el);
					return;
				}

				// Removed by DF, 9/2/2018
				// // All the work gets done here
				// for (i = Math.max(start, 0); i < len; i++) {

				// 	// The start argument and options.step limit
				// 	// the characters we will be working on at once

				// 	if (i < start + options.step) {
				// 		// Generate a random character at thsi position
				// 		strCopy[letters[i]] = randomChar(types[letters[i]]);
				// 	}
				// 	else {
				// 		strCopy[letters[i]] = "";
				// 	}
				// }
				
				// Added by DF, 9/2/2018
				for (i = Math.max(start, 0); i < start + options.step; i++){
					strCopy[letters[i]] = randomChar();
				}

				el.text(strCopy.join(""));
				
				setTimeout(function(){
					
					shuffle(start+1);
					
				},1000/options.fps);
				
			})(-options.step);
			

		});
	};
	
	function randomChar(type){
		
		// Removed by DF, 9/2/2018
		// var pool = "";
		// if (type == "lowerLetter"){
		// 	pool = "abcdefghijklmnopqrstuvwxyz0123456789";
		// }
		// else if (type == "upperLetter"){
		// 	pool = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
		// }
		// else if (type == "symbol"){
		// 	pool = ",.?/\\(^)![]{}*&^%$#'\"";
		// }
		// var arr = pool.split('');

		return arr[Math.floor(Math.random()*arr.length)];
	}
	
})(jQuery);