(function(){function L(c){var m=(c||'').match(/[\d.]+/g);if(!m)return 1;var a=m.slice(0,3).map(function(v){v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)});return 0.2126*a[0]+0.7152*a[1]+0.0722*a[2]}
function BG(e){while(e){var c=getComputedStyle(e).backgroundColor,m=(c||'').match(/[\d.]+/g);if(m&&(m.length<4||+m[3]>0.5))return c;e=e.parentElement}return 'rgb(255,255,255)'}
var bad=[],els=document.querySelectorAll('body *');
for(var i=0;i<els.length;i++){var e=els[i];
 if(e.closest('.lead-hp')||e.tagName==='SCRIPT'||e.tagName==='STYLE'||e.tagName==='NOSCRIPT')continue;
 var t='';for(var n=0;n<e.childNodes.length;n++)if(e.childNodes[n].nodeType===3)t+=e.childNodes[n].nodeValue;
 t=t.trim();if(!t)continue;
 var cs=getComputedStyle(e);if(cs.visibility==='hidden'||cs.display==='none'||+cs.opacity<0.1)continue;
 var r=e.getBoundingClientRect();if(r.width<2||r.height<2)continue;
 var f=L(cs.color),b=L(BG(e)),ratio=(Math.max(f,b)+0.05)/(Math.min(f,b)+0.05);
 if(ratio<3)bad.push({t:t.slice(0,34),cls:(e.className||e.tagName).toString().slice(0,26),color:cs.color,bg:BG(e),ratio:Math.round(ratio*100)/100});}
var inputs=[],ins=document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]),select,textarea');
for(var j=0;j<ins.length;j++){var el=ins[j];if(el.closest('.lead-hp'))continue;var c2=getComputedStyle(el);
 var pad=parseFloat(c2.paddingTop)+parseFloat(c2.paddingLeft);
 if(pad<8)inputs.push({name:el.name||el.id,padding:c2.padding,radius:c2.borderRadius});}
var de=document.documentElement;
return JSON.stringify({url:location.pathname,lowContrast:bad.slice(0,6),lowContrastCount:bad.length,unstyledInputs:inputs.slice(0,4),overflowX:de.scrollWidth>de.clientWidth+1});})()
