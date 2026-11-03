//获取路径的regionCode为请求传值
var url = window.location.href;
var	regionCode;
var complainMaaddressNameyz = false;
if(url.split("?")[1]!=undefined){
	if(url.split("&")[1]!=undefined){
		regionCode = url.split("?")[1].split("&")[1].split("=")[1];
	}else{
		regionCode = url.split("?")[1].split("=")[1];
	}
}else{
	regionCode="650000000000";
}
//家庭住址
var phoneNumcheckLogon=false;
//户籍所在地
var phoneFlagcheckLogon=false;
var complainAddressNameyz = false;
//身份证号
var complainCredentialCardyz=false;
//真实姓名
var complainNameyz=false;


$(function() {
	//户籍所在地
	$("#complainMaaddressName").blur(function() {
		var checkval11 = $('#province1').find("option:selected").val();
		var checkval22 = $('#city1').find("option:selected").val();
		var checkval33 = $('#county1').find("option:selected").val();
		$("#complainMaaddressName").val($.trim($("#complainMaaddressName").val()));
		var isHidden_city1 = $('#city1').is(":hidden");
		var isHidden_county1 = $('#county1').is(":hidden");
		// 三级都check
		if ((checkval11 == "0"||!checkval11)||(!isHidden_city1&&checkval22=='0')||(!isHidden_county1&&checkval33=='0')) {
			$("#huJiAddressNameLAB").html("<h5>请选择具体城市</h5>");
			complainAddressNameyz = false;
		}else if( $("#complainMaaddressName").val()==""){
			$("#huJiAddressNameLAB").html("<h5>请具体填写所在住址</h5>");
			complainAddressNameyz = false;
		}else if ($("#complainMaaddressName").val().length > 40) {
			$("#huJiAddressNameLAB").html("<h5>详细地址过长</h5>");
			complainAddressNameyz = false;
		}else {
			$("#huJiAddressNameLAB").html("");
			complainAddressNameyz = true;
			// 如果有县级城市保留县级城市
			if (checkval33!='0') {
				$("#complainMaaddressCode").val(checkval33);
			}else if (checkval33=='0' && checkval22!='0') {
				$("#complainMaaddressCode").val(checkval22);
			}else {
				$("#complainMaaddressCode").val(checkval11);
			}
		}
	});
});
//验证用户登录
function checkLogon() {
	$.ajax({
		url : "/user/network-user-info!checkLeaderMailLogon.action",
		type : "post",
		async : false,
		dataType : 'html',
		data : {},
		success : function(data) {
			var obj = jQuery.parseJSON(data);
			console.log(obj);
			if (obj!=false) {//登录后
				$("#hasLogin").show();
		        $("#notLogin").hide();
		        $("#userName").html(obj[0].complainName+"，欢迎您");
		        $("#regionCode").val(regionCode);
		        phoneNumcheckLogon = obj[0].complainPhonenumber;
		        phoneFlagcheckLogon = obj[0].phoneFlag;
			}
		}
	});
}
function updatePhoneNum(){

	if( phoneFlagcheckLogon == "1" && phoneNumcheckLogon != null && phoneNumcheckLogon != ""){
		window.location.href = "/html/users/updatePhone.jsp?regionCode="+regionCode+"";
	}else{
		alert("当前账号未绑定手机号，请先绑定手机号");
	}
}
// 用户名符号
function showPoint() {
	var check = /[\.|。|、|,|，|`|\*]+/;
	var zsxm = $.trim($("#zsxm").val());
	if (zsxm != "") {
		if (check.test(zsxm)) {
			$("#pointDIV").html('<h4 style="color:red;font-size:12px;">姓名中若含"<b id="fuzhidian" >·</b>"符号，请<input type="button" value="插入" onClick="cp()" style="height: 20px;font-size: 12px;"/>使用！</h4>');
		} else {
			$("#pointDIV").html('<h4 style="color:white;font-size:15px;">&nbsp;<b id="fuzhidian" >&nbsp;</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</h4>');
		}
	} else {
		$("#pointDIV").html('<h4 style="color:white;font-size:15px;">&nbsp;<b id="fuzhidian" >&nbsp;</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</h4>');
	}
}
//验证码

function changeValidateCode(obj) {
	//获取当前的时间作为参数，无具体意义
	var timenow = new Date().getTime();
	//每次请求需要一个不同的参数，否则可能会返回同样的验证码
	obj.src= "/servlet/VerifyCodeServlet?d=" + timenow;
}
//登录验证
function logOn() {
	if ($("#complainLoginName").val() == '') {
		alert("请输入用户名");
		$("#complainLoginName").focus().select();
		return false;
	} else if ($("#complainPassword").val() == '') {
		alert("请输入密码");
		$("#complainPassword").focus().select();
		return false;
	}else if ($("#vercode").val() == '') {
		alert("请输入验证码");
		$("#vercode").focus().select();
		return false;
	} else {
		var complainLoginName = $.trim($("#complainLoginName").val());
		var complainPassword = $.trim($("#complainPassword").val());
	    var vercode = $.trim($("#vercode").val());
	    //把密码加密传输  lys 2015 03 18
	    complainPassword = hex_md5(complainPassword);
	    // 登陆信息提交
	    $.ajax({
	    	//url : "/user/network-user-info!login.action?regionCode="+regionCode,
	    	url : "/user/network-user-info!login.action",
	    	type : "post",
	    	async : true,
	    	dataType: "html",
	    	data : {
				"complainLoginName" : complainLoginName,
				"complainPassword" : complainPassword,
				"vercode" : vercode,
	    	},
	    	success : function(data) {
	    		var obj = eval('(' + data + ')');
	    		if (obj.loginFlag == "true") {//登录成功
					$(function() {
						$.ajax( {
							url : "/user/network-user-info!getUserInfo1.action",
							type : "post",
							dataType : "html",
							//async : true  异步   async : false  同步
							async : true,
							date:{
								"complainCredentialCard":complainCredentialCard,
								"complainName":complainName,
							},
							success : function(data) {

								var info = jQuery.parseJSON(data);

								//没有绑定手机号 显示绑定页面 强制进行绑定
								if(obj.phoneFlag != "1"){
									document.getElementById("phoneDiv").style.display="block";
									document.getElementById("fade").style.display="block";
									var bgdiv = document.getElementById("fade");
									bgdiv.style.width = document.body.scrollWidth;
									$("#fade").height($(document).height());
									$.ajax({
										url : "/user/network-user-info!userLogOut.action",
										type : "post",
										data : {},
										type : "html",
										success : function(data) {

										},
										error : function(data) {
										}
									});

								}else{
									if(url.indexOf("login.jsp")!=-1&&url.indexOf("regionCode=650000000000")!=-1){
										window.location.href ="/html/main/index.jsp?regionCode="+regionCode;
									}else if(url.indexOf("leaderMailbox")!=-1){
										window.location.href=url;
									}else/* if(url.indexOf("login.jsp")!=-1)*/{
										//
										if(regionCode=='650000000000'){
											window.location.href="/html/onlineInquiry/onlineILsit.jsp?regionCode="+regionCode;
										}else{
											window.location.href="/html/users/index.jsp?regionCode="+regionCode;
										}
									}
								}
								/*户籍地拆分*/
								var address1 = new Array();
								if (info[0].complainMaaddressCode != "" && info[0].complainMaaddressCode != null) {
									address1 = info[0].complainMaaddressCode;
									var loc_province = address1.substring(0, 2)+"0000";// 省
									if (loc_province == "110000" || loc_province =="500000"|| loc_province =="120000"|| loc_province =="310000") {
										var loc_city = address1;// 市
										var loc_town = '0';// 区
										var complainMaaddressCode = loc_province+','+ loc_city +','+ loc_town;
										showLocationForIdCode1('province1', 'city1', 'county1', 'complainMaaddressCode',loc_province, loc_city, loc_town);
									}else if (loc_province =="810000" || loc_province =="820000") {
										var loc_city = '0';// 市
										var loc_town = '0';// 区
										var complainMaaddressCode = loc_province+','+ loc_city +','+ loc_town;
										showLocationForIdCode1('province1', 'city1', 'county1', 'complainMaaddressCode',loc_province, loc_city, loc_town);
									}else {
										var loc_city = address1.substring(0, 4)+"00";// 市
										var loc_town = address1;// 区
										var complainMaaddressCode = loc_province+','+ loc_city +','+ loc_town;
										showLocationForIdCode1('province1', 'city1', 'county1', 'complainMaaddressCode',loc_province, loc_city, loc_town);
									}
								}
								/*$("#complainMaaddressName").val(info[0].complainMaaddressName);*/

								// 证件号码
								$("#complainCredentialCard").val(info[0].complainCredentialCard);
								// 账号名
								$("#ZhangHao").val(info[0].complainLoginName);

								//地址代码
								$("#complainMaaddressCode").val(info[0].complainMaaddressCode);
								//真实姓名
								$("#complainName").val(info[0].complainName);


								// 生日和性别根据身份证号识别
								if (parseInt(info[0].complainCredentialCard.substring(6, 10)) < 1900) {
									$("#birthday").val("");
									return false;
								}
								var birthdayValue = info[0].complainCredentialCard.substring(6, 10) + "-" + info[0].complainCredentialCard.substring(10, 12) + "-"
									+ info[0].complainCredentialCard.substring(12, 14);
								$('#birthday').val(birthdayValue);// 出生日期赋值

								if (parseInt(info[0].complainCredentialCard.substr(16, 1)) % 2 == 0) {
									$("#xb").val("0");// 女
								} else {
									$("#xb").val("1");// 男
								}

							},
							error : function(rtn) {
							}
						});
					})

				} else{
					if (obj.loginFlag == "false") {
						var timenow = new Date().getTime();
			            $("#authImg").attr("src","/servlet/VerifyCodeServlet?d=" + timenow);
						alert("用户名或密码错误！");
					}
					if (obj.loginFlag == "falseVer") {
						var timenow = new Date().getTime();
			            $("#authImg").attr("src","/servlet/VerifyCodeServlet?d=" + timenow);
						alert("验证码错误！")
					}
				}
	    	},
	    	error : function() {
	    		}
			});
	}
}
var phoneNum;//发送短信验证码的手机号
var phoneCode;//验证码
//* /^(1[0-9]{10})$/ // 手机正则表达式
var reg = /^1(3[0-9]|4[01456879]|5[0-35-9]|6[2567]|7[0-8]|8[0-9]|9[0-35-9])\d{8}$/;
var clock = '';

var nums = 60;
var btn;
var codeFlag = false;
function selectCode(thisBtn){
	codeFlag = true;
	//获取手机号
	phoneNum = $("#phoneNum").val();
	if(!("" == phoneNum)){
		if(reg.test(phoneNum)){
			//发请求获取验证码
			$.ajax({
		    	url : "/user/network-user-info!getPhoneCodefromHtml.action",
		    	type : "post",
		    	async : true,
		    	dataType: "html",
		    	data : {
					"phoneNum" : phoneNum,
					"typeFrom" : "login"
		    	},
		    	success : function(data) {
		    		var obj = eval('(' + data + ')');
		    		if (obj.logonFlag == "true") {//登录成功
		    			btn = thisBtn;
		    			btn.disabled = true; //将按钮置为不可点击
		    			btn.value = nums+'秒后可重新获取';
		    			clock = setInterval(doLoop, 1000); //一秒执行一次
		    		}else{
						if (obj.message) {
							alert(obj.message);
						} else {
							alert("当前手机号未查询到绑定信息，请先进行绑定再使用短信验证码登录！")
						}
		    		}
		    	},
		    	error : function() {
		    		}
				});
		}else{
			alert("输入手机号码的格式不正确！")
		}
	}else{
		alert("请输入手机号！")
	}
}
function doLoop() {
	nums--;
	if (nums > 0) {
		btn.value = nums + '秒后可重新获取';
	} else {
		clearInterval(clock); // 清除js定时器
		btn.disabled = false;
		btn.value = '获取验证码';
		nums = 60; //重置时间
	}
}
function registerSelectCode(thisBtn){
	codeFlag = true;
	//获取手机号
	phoneNum = $("#registerPhoneNum").val();
	if(!("" == phoneNum)){
		if(reg.test(phoneNum)){
			//发请求获取验证码
			$.ajax({
		    	url : "/user/network-user-info!getPhoneCodefromHtml.action",
		    	type : "post",
		    	async : true,
		    	dataType: "html",
		    	data : {
		    		"phoneNum" : phoneNum,
					"typeFrom" : "register"
		    	},
		    	success : function(data) {
		    		var obj = eval('(' + data + ')');

		    		if (obj.logonFlag == "true") {//登录成功
		    			btn = thisBtn;
		    			btn.disabled = true; //将按钮置为不可点击
		    			btn.value = nums+'秒后可重新获取';
		    			clock = setInterval(doLoop, 1000); //一秒执行一次
		    		}else{
						if (obj.message) {
							alert(obj.message);
						} else {
							alert("当前手机号已被绑定，请核实！")
						}
		    		}
		    	},
		    	error : function() {
		    		}
				});
		}else{
			alert("输入手机号码的格式不正确！")
		}
	}else{
		alert("请输入手机号！")
	}
}
//验证码登陆
function logOnByPhoneCode(){
	//登陆时手机号
	var phone = $("#phoneNum").val();
	//输入的短信验证码
	var code = $("#phoneCode").val();
	if(!("" == phone)){
		if(codeFlag){
			$.ajax({
		    	//url : "/user/network-user-info!login.action?regionCode="+regionCode,
		    	url : "/user/network-user-info!loginByPhoneCode.action",
		    	type : "post",
		    	async : true,
		    	dataType: "html",
		    	data : {
					"complainPhonenumber" : phone,
					"phoneCode" : code
		    	},
		    	success : function(data) {
		    		var obj = eval('(' + data + ')');
		    		if (obj.loginFlag == "true") {//登录成功
		    			if(url.indexOf("login.jsp")!=-1&&url.indexOf("regionCode=650000000000")!=-1){
		    				window.location.href ="/html/main/index.jsp?regionCode="+regionCode;
		    			}else if(url.indexOf("leaderMailbox")!=-1){
		    				window.location.href=url;
		    			}else/* if(url.indexOf("login.jsp")!=-1)*/{
		    				//
		    				if(regionCode=='650000000000'){
		    					window.location.href="/html/onlineInquiry/onlineILsit.jsp?regionCode="+regionCode;
		    				}else{
		    					window.location.href="/html/users/index.jsp?regionCode="+regionCode;
		    				}
		    			}
					}else {
						if (obj.loginFlag == "false") {
							var timenow = new Date().getTime();
				            $("#authImg").attr("src","/servlet/VerifyCodeServlet?d=" + timenow);
							alert("用户名或验证码错误！");
						}
						if (obj.loginFlag == "falseVer") {
							var timenow = new Date().getTime();
				            $("#authImg").attr("src","/servlet/VerifyCodeServlet?d=" + timenow);
							alert("验证码错误！")
						}
					}
		    	},
		    	error : function() {
		    		}
				});
		}else{
			alert("请获取验证码！")
		}
	}else{
		alert("请输入手机号并获取验证码！")
	}
}
function CloseDiv(show_div,bg_div){

	document.getElementById(show_div).style.display="none";
	document.getElementById(bg_div).style.display="none";
	var url = window.location.href;
	//alert(url);
	if(url.indexOf("login.jsp")!=-1&&url.indexOf("regionCode=650000000000")!=-1){
		window.location.href ="/html/main/index.jsp?regionCode="+regionCode;
	}else if(url.indexOf("leaderMailbox")!=-1){
		window.location.href=url;
	}else/* if(url.indexOf("login.jsp")!=-1)*/{
		//
		if(regionCode=='650000000000'){
			window.location.href="/html/onlineInquiry/onlineILsit.jsp?regionCode="+regionCode;
		}else{
			window.location.href="/html/users/index.jsp?regionCode="+regionCode;
		}
	}
}
//绑定手机号确认按钮方法
function registerPhone(){
	//登陆时手机号
	var phone = $("#registerPhoneNum").val();
	//输入的短息验证码
	var code = $("#registerPhoneCode").val();
	//身份证
	var card = $("#complainCredentialCard").val();
	var ZhangHao = $("#complainLoginName").val();
	//真实姓名
	var userRealName = $("#complainName").val();
	//生日
	var birthday = $("#birthday").val()
	//性别
	var xb = $("#xb").val();
			// 生日和性别根据身份证号识别
			// showBirthday($('#complainCredentialCard'), $('#birthday'), $('#xb'));

	if (parseInt(card.substring(6, 10)) < 1900) {
		$("#birthday").val("");
		return false;
	}
	var birthdayValue = card.substring(6, 10) + "-" + card.substring(10, 12) + "-"
				+ card.substring(12, 14);
	$('#birthday').val(birthdayValue);// 出生日期赋值
			if (parseInt(card.substr(16, 1)) % 2 == 0) {

				$("#xb").val("0");// 女
			} else {
				$("#xb").val("1");// 男
			}


	var complainMaaddressName = $("#complainMaaddressName").val();
//户籍地代码
	var complainMaaddressCode = $("#complainMaaddressCode").val();
	if (""==complainMaaddressCode ||""==complainMaaddressName){
		alert("请输入地址")
		return false;
	}

		if ((!("" == card)) && card.length == 18) {
			if (!("" == userRealName)) {
				$.ajax({
					//url : "/user/network-user-info!login.action?regionCode="+regionCode,
					url: "/user/network-user-info!sfzBangDing.action",
					type: "post",
					async: true,
					dataType: "html",
					data: {
						"complainCredentialCard": card,
						"complainName": userRealName,

					},
					success: function (data) {
						var obj = eval('(' + data + ')');
						if (obj.message == '0') {//登录成功
							if (!("" == phone)) {
								if (!("" == code)) {
									$.ajax({
										//url : "/user/network-user-info!login.action?regionCode="+regionCode,
										url: "/user/network-user-info!userRealtionPhone.action",
										type: "post",
										async: true,
										dataType: "html",
										data: {
											"phone": phone,
											"code": code,
											"complainCredentialCard": card,
											"complainName": userRealName,
											"complainMaaddressName": complainMaaddressName,
											"complainMaaddressCode": complainMaaddressCode,
											"complainBirthday": birthday,
											"complainSex": xb,
											"complainLoginName":ZhangHao,
										},
										success: function (data) {
											var obj = eval('(' + data + ')');
											if (obj.loginFlag == "true") {//登录成功
												alert("绑定成功,请重新登录");
												CloseDiv("phoneDiv", "fade");
											} else {
												alert(obj.message);
											}
										},
										error: function () {
										}
									});
								} else {
									alert("请输入短信验证码！")
								}
							} else {
								alert("请输入手机号！")
							}
						} else if (obj.message == '5') {
							alert("身份证与姓名不匹配！")
						} else if (obj.message == '14') {
							alert("无此身份证号码！")
						} else if (obj.message == '96') {
							alert("交易失败，请稍后重试！")
						} else if (obj.message == '100') {
							alert("请联系客服客服！")
						} else if (obj.message == '2') {
                            alert("此身份证已绑定!")
						}
					},
					error: function () {
					}
				});
			} else {
				alert("请输入名字！")
			}
		} else {
			alert("请输入正确身份证号！")
		}
	}

