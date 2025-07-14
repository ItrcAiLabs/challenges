(function () {

    'use strict';
    angular.module('evalai')
        .filter('e2p', convert_to_persian_number);

    function convert_to_persian_number() {
        return function (n) {
            const farsiDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];

            return n
                .toString()
                .replace(/\d/g, x => farsiDigits[x]);
        };

    }

    angular.module('evalai')
        .filter('jalali', convert_to_jalali);

    function convert_to_jalali() {
        return function (input) {
            var myArray = input.split("/");
            var gy = parseInt(myArray[0]);
            var gm = parseInt(myArray[1]);
            var gd = parseInt(myArray[2]);
            var g_d_m, jy, jm, jd, gy2, days;
            g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
            gy2 = (gm > 2) ? (gy + 1) : gy;
            days = 355666 + (365 * gy) + ~~((gy2 + 3) / 4) - ~~((gy2 + 99) / 100) + ~~((gy2 + 399) / 400) + gd + g_d_m[gm - 1];
            jy = -1595 + (33 * ~~(days / 12053));
            days %= 12053;
            jy += 4 * ~~(days / 1461);
            days %= 1461;
            if (days > 365) {
                jy += ~~((days - 1) / 365);
                days = (days - 1) % 365;
            }
            if (days < 186) {
                jm = 1 + ~~(days / 31);
                jd = 1 + (days % 31);
            } else {
                jm = 7 + ~~((days - 186) / 30);
                jd = 1 + ((days - 186) % 30);
            }

            return jy + '/' + jm + '/' + jd;

        };

    }
})();
