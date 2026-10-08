 // JavaScript Document
//导航下拉菜单
function menu_show(num){
	var i=num;
	document.getElementById("menu"+i).style.display="";
	document.getElementById("tab"+i).className="meng_nav_off";
	$(".meng_nav_off a").css({"color":"#fff"});
		for(var j=1;j<8;j++)
		{
				if(j!=i)
				{
				document.getElementById("menu"+j).style.display="none";
				document.getElementById("tab"+i).className="meng_nav_on";
				$(".meng_nav_on a").css({"background":"#fff","color":"#af1f1e"});
				}
				
			}
}
function menu_dis(num){
	document.getElementById("menu"+num).style.display="none";
	document.getElementById("tab"+num).className="meng_nav_off";
$(".meng_nav_off a").css({"background":"","color":"#fff"});

	}