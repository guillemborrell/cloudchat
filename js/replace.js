// Replace text
var brvs_rpl = new Object();
brvs_rpl.rpl_rules = new Array();

function rpl_rule(find_str,rpl_str){
    this.find = find_str;
    this.rpl = rpl_str;
    return this;
}

brvs_rpl.append = function(find_str,rpl_str){
    this.rpl_rules.push(new rpl_rule(find_str,rpl_str));
}

// IMG url
brvs_rpl.append(
    /[^(\<p\>)](\<img[\w\-\.\=\"\:\/\s]+\>)[^(\<\/p\>)]/ig,
    ' <p>$1</p> '
);

brvs_rpl.append(
    /[^\"\'](https?\:\/\/[\w\.\/\-]+\.(jpg|jpeg|png|gif|bmp))\??[\w\.\/\-\=\?\&\%]*[^\"\']/ig,
    ' <p><img src="$1" /></p> '
);

// YouTube url
brvs_rpl.append(
    /https?:\/\/(?:[0-9A-Z-]+\.)?(?:youtu\.be\/|youtube\.com\S*[^\w\-\s])([\w\-]{11})(?=[^\w\-]|$)(?![?=&+%\w]*(?:['"][^<>]*>|<\/a>))[?=&+%\w-]*/ig,
    ' <iframe width="285" height="214" src="http://www.youtube.com/embed/$1" frameborder="0" allowfullscreen></iframe> '
);

// LINK url
brvs_rpl.append(
    /[^\"\'](https?\:\/\/[\w\.\/\-\=\?\&\%]+)[^(jpg|jpeg|png|gif|bmp)][^\"\']/ig,
    ' <a href="$1">link</a> '
);




// New Line
brvs_rpl.append(
    /(\n)/ig,
    '<br />'
);



$(document).ready(function(){
    $(".message-content").each(function(i){
        txt = $(this).html();
        for (var I in brvs_rpl.rpl_rules){
            ch_txt = ' '+txt+' ';
            txt = ch_txt.replace(
                brvs_rpl.rpl_rules[I].find,
                brvs_rpl.rpl_rules[I].rpl
            );
            
            if(txt[0]==' '){
                txt = txt.substr(1);
            }
            if(txt[txt.length-1]==' '){
                txt = txt.substr(0,txt.length-1);
            }
        }
        txt="<div class='message-content'>"+txt+"</div>";
       $(this).replaceWith(txt); 
    });
    document.getElementById('new-message').focus();
});