function loadMessageList() {
      // var  url = "../xf-link/js/index.json";
      var url = '../xfwy/jsonFiles/index.json';
      $.getJSON(url, function (data) {
            var result = data;
            var lydf = $("#lydf").html();
            var lyxd = $("#lyxd").html();
            var lybl = $("#lybl").html();
            var lytj = $("#lytj").html();

            var tpl_lydf = Handlebars.compile(lydf);
            var tpl_lyxd = Handlebars.compile(lyxd);
            var tpl_lybl = Handlebars.compile(lybl);
            var tpl_lytj = Handlebars.compile(lytj);

            Handlebars.registerHelper('handleDate', function(date) {
                return date.substring(5);
            });

            Handlebars.registerHelper('getMonth', function(month) {

                if (month < 10) {
                    month = '0' + month;
                }

                return month;
            });

            var html_lydf = tpl_lydf(result);
            var html_lyxd = tpl_lyxd(result);
            var html_lybl = tpl_lybl(result);
            var html_lytj = tpl_lytj(result);

            $("#lydfContent").html(html_lydf);
            $("#lyxdContent").html(html_lyxd);
            $("#lyblContent").html(html_lybl);
            $("#lytjContent").html(html_lytj);

      })
}
