
function AsopDomain(){
	
	
	this.buildRangeNumber=function(min,max,minInclusive,maxInclusive){
		var mi=minInclusive?"=":"";
		var ma=maxInclusive?"=":"";
		if((!min)&&(!max)){//最大，最小都为空
			return '';
		}
		
		var s=[];
		var i=0;
		s[i++]=min;
		s[i++]=mi;
		s[i++]="-";
		s[i++]=ma;
		s[i++]=max;
		return s.join("");
	}
}