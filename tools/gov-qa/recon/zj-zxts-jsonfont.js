//version=1.0.0
var MutationObserver = window.MutationObserver || window.WebKitMutationObserver || window.MozMutationObserver;
let callback, observer;
callback = function (record) {
	record.forEach(function (mutation) {
		if (mutation.type === 'characterData') {
			let node = mutation.target.parentNode;
			const value = node.innerText;
			if (value && value.lastIndexOf("otltag") > -1) {
				resolve(node, node.innerText);
			}
		} else if (mutation.type === 'childList') {
			let num = mutation.addedNodes.length;
			let i=0;
			for(i=0;i<num;i++) {
				let node = mutation.addedNodes[i];
				if (node) {
					let nodeName = node.nodeName;
					if (nodeName === '#text') {
						//let text = node.nodeValue;
						//console.log('[ZBINFO-text]:'+text)
						resolveTextNode(node,node.nodeValue);
					} else {
						//let text = node.innerText;
						//console.log('[ZBINFO-node:]:'+text)
						resolveNode(node);
					}
				}
			}
		}else{
			//console.log(mutation.type+' '+mutation.attributeName);
		}
	})
}
observer = new MutationObserver(callback);
const node = document.querySelector("html");
const options = {
	'childList': true,
	'attributes': true,
	'characterData': true,
	'subtree': true,
	'characterDataOldValue': true
};
observer.observe(node, options);

document.addEventListener('DOMContentLoaded', function() {

	addToolTip();
});


mutationObserver.observe(node, options);

function intersectionCallback(entries,observer){
	entries.forEach(entry =>{
		if(entry.isIntersecting){
			//console.log(entry.target.textContent);
			var start = performance.now();
			changeNode(entry.target);
			var end = performance.now();
			//console.log('cost:'+(start - end));
			//console.log(end-start);
		}else{

		}
	});
}
var options2={threshold:0.25};
var intersectionObserver = new IntersectionObserver(intersectionCallback,options2);

function addIntersectionObserver(node){
	intersectionObserver.observe(node);
}
function getAll() {
	var objs = document.all;

	var length1;
	for (var i = 0; i < objs.length; i++) {
		var obj = objs[i].tagName;
		if (obj == "body" || obj == "BODY") {
			length1 = i + 1;
			break;
		}
	}
	var b_objs = new Array();
	for (var j = length1; j < objs.length; j++) {
		b_objs.push(objs[j]);
	}

	debugger;
	return b_objs;
}

/**
 * 遍历所有节点，找到包含otl标签的那个节点
 * @param parentNode
 */
function resolveNode(parentNode) {
	const length = parentNode.childNodes.length;
	for (let i = 0; i < length; i++) {
		const child = parentNode.childNodes[i];
		if (child.childNodes.length >= 1) {
			const innerText = child.innerText;
			if(innerText && innerText.lastIndexOf("otltag") > -1) {
				resolveNode(child);
			}
		} else {
			if (child.nodeName !== '#text'){
				const innerText = child.innerText;
				if (innerText && innerText.lastIndexOf("otltag") > -1) {
					resolve(child, innerText);
				}
			}else{
				const innerText=child.wholeText;
				if (innerText && innerText.lastIndexOf("otltag") > -1) {
					resolveTextNode(child, innerText);
				}
			}
		}
	}
}

function resolveTextNode(textNode,value) {
	var patt1 = new RegExp("(?:#)[a-zA-Z0-9_]*?(?=otltag)", "g");
	var rets = patt1.exec(value);

	if(!rets) {
		//适配国办json加密
		//console.log("error:font is null" + value);
		var attrs = textNode.parentNode.attributes;
		for (const attr of attrs) {
			if (attr.nodeName === 'title') {
				value = attr.nodeValue;
			}
		}
		rets = patt1.exec(value);
		if (!rets) {
			return;
		}
	}
	var fontRets = new Array();
	for (var i = 0; i < rets.length; i++) {
		rets[i] = rets[i].substr(1);
		var objindex = findAll(fontRets, rets[i]);
		if (objindex.length == 0) {
			fontRets.push(rets[i]);
		}
		if ($("#" + rets[i]).length == 0) {
			addCss(rets[i]);
		}
	}
	var ft = "";
	for (var i = 0; i < fontRets.length; i++) {
		ft = "cfg_" + fontRets[i] + ft
	}
	var value1 = value;
	value1 = value1.replace(/(?:#)[\s\S]*?(?:otltag)/g, '');
    value1 = value1.replace(/#FontTag/g, '');
	textNode.parentNode.setAttribute('style','font-family:'+ft);
	textNode.nodeValue=value1;
}

function resolve(that, value) {
	var patt1 = new RegExp("(?:#)[a-zA-Z0-9_]*?(?=otltag)", "g");
	var rets = patt1.exec(value);
	var fontRets = new Array();
	for (var i = 0; i < rets.length; i++) {
		rets[i] = rets[i].substr(1);
		//alert(rets[i]);
		var objindex = findAll(fontRets, rets[i]);
		if (objindex.length == 0) {
			fontRets.push(rets[i]);
		}
		if ($("#" + rets[i]).length == 0) {
			addCss(rets[i]);
		}
	}
	var ft = "";
	for (var i = 0; i < fontRets.length; i++) {
		ft = "cfg_" + fontRets[i] + ft
	}
	var value1 = value;

	//去标签替换
	//value1 = value1.replace(/(?:#)[\s\S]*?(?:otltag)/g, '<font style=\"font-family:' + ft + "\"" + ">");
	//value1 = value1.replace(/#FontTag/g, "</font>");
	value1 = value1.replace(/(?:#)[\s\S]*?(?:otltag)/g, '');
	value1 = value1.replace(/#FontTag/g, '');

	if (that.nodeName === '#text') {
		$(that).val(value1);
	}
	else if (that.tagName == "input" || that.tagName == "textarea"
		|| that.tagName == "INPUT" || that.tagName == "TEXTAREA") {
		$(that).val(value1);

	} else {
		let nodeT=that.childNodes[0];
		if(nodeT){
			//if(nodeT.nodeName ==='#text'){
			if(nodeT.nodeName === '#text'  ){
				that.setAttribute('style','font-family:'+ft);
				nodeT.nodeValue=value1;
			}else if(nodeT.nodeName === 'SPAN'){
				nodeT.setAttribute('style','font-family:'+ft);
				(nodeT).innerText=value1;
			}else if(nodeT.nodeName === 'DIV'){
				nodeT.setAttribute('style','font-family:'+ft);
				(nodeT).innerText=value1;
			}
		}else{
			$(that).html(value1);
		}
	}
	return value1;
}

function addCss(id) {
	var preloadElement = document.createElement("link");
     preloadElement.rel = "preload";
     preloadElement.href = "/zlh/zsapi/ttf/" + id + ".woff";
     preloadElement.as = "font";
    document.getElementsByTagName("head")[0].appendChild(preloadElement);
	var cssCode = "@font-face{	font-display:block;    font-family : 'cfg_" + id
		+ "';		src:url('/zlh/zsapi/ttf/" + id + ".eot');		src:url('/zlh/zsapi/ttf/" + id
		+ ".eot?#iefix') format('embedded-opentype'),url('/zlh/zsapi/ttf/" + id
		+ ".woff') format('WOFF');	}.clz_" + id + " {"
		+ "\tfont-family: cfg_" + id + " !important;" + "}";
	var styleElement = document.createElement("style");
	styleElement.id = id;
	styleElement.type = "text/css";
	if (styleElement.styleSheet) {
		styleElement.styleSheet.cssText = cssCode;
	} else {
		styleElement.appendChild(document.createTextNode(cssCode));
	}
	document.getElementsByTagName("head")[0].appendChild(styleElement);
}

function addToolTip() {
	var code="titleTooltip({\n" +
		"        onShow: function(reference, popper){\n" +
		"            popper.hidden = false;\n" +
		"            position.default({\n" +
		"                target    : popper,\n" +
		"                useRaf    : false,\n" +
		"                ref       : reference,\n" +
		"                offset    : [0],\n" +
		"                placement : \"center below\",\n" +
		"            })\n" +
		"        },\n" +
		"        onHide: function(reference, popper) {\n" +
		"            popper.hidden = true;\n" +
		"\n" +
		"        }\n" +
		"    })";
	var styleElement = document.createElement("script");
	if (styleElement.styleSheet) {
		styleElement.styleSheet.cssText = code;
	} else {
		styleElement.appendChild(document.createTextNode(code));
	}
	document.getElementsByTagName("body")[0].appendChild(styleElement);
}
function findAll(a, x) {
	var results = [],
		len = a.length,
		pos = 0;
	while (pos < len) {
		pos = a.indexOf(x, pos);
		if (pos === -1) {
			break;
		}
		results.push(pos);
		pos += 1;
	}
	return results;
}

