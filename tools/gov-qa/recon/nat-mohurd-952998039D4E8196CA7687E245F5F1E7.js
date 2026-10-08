//cookies 取值
function getCookie01(name){
	var strcookie = document.cookie;//获取cookie字符串
	var arrcookie = strcookie.split("; ");//分割
	//遍历匹配
	for ( var i = 0; i < arrcookie.length; i++) {
		var arr = arrcookie[i].split("=");
		if (arr[0] == name){
			return arr[1];
		}
	}
	return "";
}
// getCookie01("web-access-token")

//cookies 删除值
function delCookie(name){
	var exp = new Date();
	exp.setTime(exp.getTime() - 1);
	var cval=getCookie01(name);
	if(cval!=null)
	document.cookie= name + "="+cval+";expires="+exp.toGMTString();
}
		
var xsign = '';
var nwebToken = '{"web-access-token":"'+ getCookie01("web-access-token") +'"}'
var timetamp = Math.round(new Date().getTime());
var loganSat = false;



var newObj = {
	'app_id':'bjzjb-transfer',
	'interface_id':'web_login_getCurrentUser',
	'version':'1.0',
	'header':nwebToken,
	'biz_content':'{}',
	'app_id':'bjzjb-transfer',
	'charset':'UTF-8',
	'timestamp':timetamp,
	'origin':'PC'
};


function getWebToken(newobj){
	console.log("获取签证",newobj)
	//获取签证
	$.ajax({
		url:'/api-gateway/jpaas-jags-server/interface/createsign.do',
		type: 'POST',
		dataType: 'json',
		data:newobj,
		//async: false,
		success: function(result){
			//console.log(result);
			//console.log(result.data.sign);
			getInfo(result.data.sign,newobj);
		}
	})
}


function getInfo(str,newobj){
	console.log(str)
	newobj['sign'] = str; 
	console.log(newobj)
	$.ajax({
		url:'/api-gateway/jpaas-jags-server/interface/gateway',
		type: 'POST',
		dataType: 'json',
		data:newobj,
		//async: false,
		success: function(result){
			//console.log(result)
			
			if(result.success){
				//console.log(result.data);
				//console.log(JSON.parse(result.data));
				let nData = JSON.parse(result.data);
				if(nData.code == '20000'){
					//console.log('登录成功')
					//console.log(nData.data.resultData)
					var codeContent = nData.data.resultData;
					var nmyCode = getCookie01("web_p_k");
					var newResult = sm2.doDecrypt(codeContent.slice(2), nmyCode, 1)
					newResult = JSON.parse(newResult)
					//console.log(newResult)
					
					$(".user-info").removeClass("disnone");
					$(".login-action").addClass("disnone");
					
					//$("#name").val(newResult.displayName)
                    $("#xm").val(newResult.displayName)
					$("#mphone").val(newResult.mobile)
					//$("#idcard").val(newResult.cardNum)
                    $("#sfzh").val(newResult.cardNum)
					$(".user-info-about > span").text(newResult.displayName);
                  	$("#xm").attr("readonly",true)
                  	$("#mphone").attr("readonly",true)
                  	$("#sfzh").attr("readonly",true)
                  	loganSat = true;
				}else{
					$(".login-action").removeClass("disnone");
					$(".user-info").addClass("disnone");
                   // alert('登录失效');
					// var confirmResult = window.confirm("当前登录已失效，请重新登录");
					// if (confirmResult) {
					// 	// console.log("重新登陆");
					// 	window.parent.location.href = '/hanweb-bjzjb-transfer-server/front/web-login/goLoginPage/hudong'
					// } else {
					// 	console.log("关闭窗口");
					// }

				}
			}
			
		}
	})
}

$(function(){
	if(getCookie01("web-access-token") != "" ){
		let nwebTokenValue =  getCookie01("web-access-token");
		newObj['web-access-token'] = nwebTokenValue; 
		getWebToken(newObj)
		$(".user-info").removeClass("disnone");
		$(".login-action").addClass("disnone");
	}else{
		$(".login-action").removeClass("disnone");
		$(".user-info").addClass("disnone");
	}
/*
	// 登录
	$("#login-btn").click(function(){
		window.parent.location.href = '/hanweb-bjzjb-transfer-server/front/web-login/goLoginPage/hudong'
	})
	// 注册
	$("#register-btn").click(function(){
		window.parent.location.href = 'https://zwfwzjb.mohurd.gov.cn/zjb-tysf-qy/zjyhtx/memlogin/personal_registered.html?redirect_uri='+window.parent.location.href;
	})
	// http://new.mohurd.gov.cn/hudong/zwzx/wytw/index.html
	// 退出
	$('.user-log-out span').click(function(){
		document.cookie = "web-access-token=;domain=mohurd.gov.cn; Expires=Thu Jan 01 08:00:00 CST 1970; path=/";
		document.cookie = "web_p_k=;domain=mohurd.gov.cn; Expires=Thu Jan 01 08:00:00 CST 1970; path=/";
		window.parent.location.href = 'https://zwfwzjb.mohurd.gov.cn/zjb-tysf-qy/rest/oauth2/logout?redirect_uri='+escape(window.parent.location.href)
	})
*/			
})