
			function screendemo() {
				var cssstr = $("#cssdemo").attr("href");
				var str_beforeinde = cssstr.lastIndexOf('/');
				var str_con = cssstr.substr(str_beforeinde);　　
				var str_before = cssstr.split(str_con)[0];
				
				var css1 = document.getElementById("cssdemo")
				var scrwid = $(window).width();
				if(scrwid >= 1200) {	
//					修改  sd_hd_px 为直接的css文件名
					css1.href = str_before + "/sd_hd_px.css";
				}
				if(1200 > scrwid && scrwid >= 992) {	
						//修改  sd_hd_pc 为直接的css文件名
					css1.href = str_before + "/sd_hd_pc.css";
				}
				if(scrwid < 992 && scrwid >= 768) {
						//修改  sd_hd_ipad 为直接的css文件名
					css1.href = str_before + "/sd_hd_ipad.css";
				}
				if(scrwid < 768) {
						//修改  sd_hd_iphone 为直接的css文件名
					css1.href = str_before + "/sd_hd_iphone.css";
				}

			}

			window.onload = function() {
				screendemo();
			};

			window.onresize = resize;

			function resize() {
				screendemo();
				
				//用通用的头尾需要下面两行！！！放开注释就好
//				screentop();
//				screenfooter();
			}
