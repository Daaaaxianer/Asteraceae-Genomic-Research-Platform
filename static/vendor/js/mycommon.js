//region URL

function seturl(key, value, href) {

    if (href.indexOf('?') === -1) href += '?';

    var searchreg = new RegExp("&?" + key + "=((?!&).)*&?");

    var kvstr = "&" + key + "=" + value;

    if (value !== "") {

        if (String.prototype.match.call(href, searchreg)) {

            var anchor = getanchor(href);

            href = href.replace(anchor, '');

            href = String.prototype.replace.call(href, searchreg, kvstr + "&");

            if (href.substr(href.length - 1, 1) === "&") href = href.substr(0, href.length - 1);

            if (href.substr(href.length - 1, 1) === "?" && href.indexOf("&") === -1) href = href.substr(0, href.length - 1);

            href += anchor;

        }

        else {

            var anchor = getanchor(href);

            href = href.replace(anchor, '');

            if (href.substr(href.length - 1, 1) === "&") href = href.substr(0, href.length - 1);

            href += kvstr;

            //if (href.substr(href.length - 1, 1) === "?" && href.indexOf("&") === -1) href = href.substr(0, href.length - 1);

            href += anchor;

        }

    } else {

        if (String.prototype.match.call(href, searchreg)) {

            var anchor = getanchor(href);

            href = href.replace(anchor, '');

            href = String.prototype.replace.call(href, searchreg, "&");

            if (href.substr(href.length - 1, 1) === "&") href = href.substr(0, href.length - 1);

            if (href.substr(href.length - 1, 1) === "?" && href.indexOf("&") === -1) href = href.substr(0, href.length - 1);

            href += anchor;

        }

        else {

            if (href.substr(href.length - 1, 1) === "&") href = href.substr(0, href.length - 1);

            if (href.substr(href.length - 1, 1) === "?" && href.indexOf("&") === -1) href = href.substr(0, href.length - 1);

        }

    }

    return href;

}



function getanchor(url) {

    url = url.match(/&?#.*$/g, "");

    if (url) {

        url = url[0];

        if (url.substr(0, 1) === "&") url = url.substr(1)

    }

    else

        url = "";



    url = url.replace(/[#]+/g, "#");

    return url;

}



function setanchor(anchor, url) {

    url = url.replace(/&?#.*$/g, "");

    url += "#" + anchor;

    return url;

}



function getMyQueryString(name) {

    var reg = new RegExp("(^|&)" + name + "=([^&]*)(&|$)");

    var r = window.location.search.substr(1).match(reg);

    if (r != null) return decodeURI(r[2]);

    return null;

}



//endregion



//#region 鍒嗛〉

function pageprev() {

    var curpage = Number(getMyQueryString('page'));

    if (curpage > 1) {

        curpage--;

    }

    var url = seturl('page', curpage, location.href);

    location.href = url;

}



function pagenext(pgcount) {

    var curpage = Number(getMyQueryString('page'));

    curpage = curpage ? curpage : 1;

    if (curpage < Number(pgcount)) {

        curpage++;

    }

    var url = seturl('page', curpage, location.href);

    location.href = url;

}



function pageto(curpage) {

    var url = seturl('page', curpage, location.href);

    location.href = url;

}



function pageprev2() {

    var curpage = Number(getMyQueryString('page2'));

    if (curpage > 1) {

        curpage--;

    }

    var url = seturl('page2', curpage, location.href);

    location.href = url;

}



function pagenext2(pgcount) {

    var curpage = Number(getMyQueryString('page2'));

    curpage = curpage ? curpage : 1;

    if (curpage < Number(pgcount)) {

        curpage++;

    }

    var url = seturl('page2', curpage, location.href);

    location.href = url;

}



function pageto2(curpage) {

    var url = seturl('page2', curpage, location.href);

    location.href = url;

}



function mypageprev(index) {

    var i = index ? index : "";

    var curpage = Number(getMyQueryString('page' + i));

    if (curpage > 1) {

        curpage--;

    }

    var url = seturl('page' + i, curpage, location.href);

    location.href = url;

}



function mypagenext(pgcount, index) {

    var i = index ? index : "";

    var curpage = Number(getMyQueryString('page' + i));

    curpage = curpage ? curpage : 1;

    if (curpage < Number(pgcount)) {

        curpage++;

    }

    var url = seturl('page' + i, curpage, location.href);

    location.href = url;

}



function mypageto(curpage, index) {

    var i = index ? index : "";

    var url = seturl('page' + i, curpage, location.href);

    location.href = url;

}



//#endregion



//#region form

function inputfileChange() {

    //鍦╥nput[type=file]鐢╟all璋冪敤姝ゆ柟娉曪紝this浠ｈ〃input,濡傦細inputfileChange.call(this)

    //闇€瑕乯query鏀寔

    var val = this.value.toLowerCase();

    if (val.right(5) !== ".jpeg" && val.right(4) !== '.jpg' && val.right(4) !== '.png') {

        layer.alert("鍥剧墖鍙敮鎸乯pg鎴杙ng鏍煎紡锛�", function () {

            layer.closeAll();

        });

        var par = $(this).parent("*").eq(0);

        var name = $(this).attr('name');

        var that = $("<input type='file' name='" + name + "' />");

        $(this).remove();

        par.prepend(that);

    }

}



//#endregion



//region 瀛楃涓�

String.prototype.left = function (length) {

    if (length <= this.length) {

        return this.substr(0, length);

    }

    else {

        return this;

    }

};

String.prototype.right = function (length) {

    if (length <= this.length) {

        return this.substr(this.length - length, length);

    }

    else {

        return this;

    }

};

String.prototype.insertStr = function (location, str) {

    if (location <= this.length - 1) {

        var l = this.left(location);

        var r = this.replace(l, "");

        return (l + str + r);

    }

    else {

        return (this + str);

    }

};

String.prototype.Trim = function () {

    return this.replace(/(^\s*)|(\s*$)/g, "");

};

String.prototype.LTrim = function () {

    return this.replace(/(^\s*)/g, "");

};

String.prototype.Rtrim = function () {

    return this.replace(/(\s*$)/g, "");

};

String.prototype.setURL = function (key, val) {

    return seturl(key, val, this);

};

String.prototype.removeAnchor = function (key, val) {

    var anc = getanchor(this);

    return this.replace(anc, "", this);

};



//endregion



