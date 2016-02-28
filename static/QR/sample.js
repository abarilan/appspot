
var draw_qrcode = function(text, typeNumber, errorCorrectLevel) {
	document.write(create_qrcode(text, typeNumber, errorCorrectLevel) );
};

var create_qrcode = function(text, typeNumber, errorCorrectLevel, table) {

	var qr = qrcode(typeNumber || 8, errorCorrectLevel || 'M');
	qr.addData(text);
	qr.make();

//	return qr.createTableTag(5);
	return qr.createImgTag(5);
};

var update_qrcode = function(text) {
//	if (screen.width >= 800) {
		var text = text.replace(/^[\s\u3000]+|[\s\u3000]+$/g, '');
		document.getElementById('qr_code').innerHTML = create_qrcode(text);
//	}
};
