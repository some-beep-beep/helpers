"""Тесты матчинга: python3 tools/astro-forum-watch/test_match.py"""
import unittest

import match


def res(title, body="", cfg=None):
    return match.analyze(title, body, cfg)


def cam(title, body=""):
    return res(title, body)["camera"]


def wheel(title, body=""):
    return res(title, body)["wheel"]


def scope(title, body=""):
    return res(title, body)["scope"]


class CameraTests(unittest.TestCase):
    def test_cyrillic_homoglyphs_asi533mm_pro(self):
        r = cam("ASI533ММ Pro")  # «ММ» кириллицей
        self.assertEqual(r["level"], "found")
        self.assertIn("ZWO ASI533MM", r["models"])
        self.assertGreaterEqual(r["score"], 14)

    def test_color_camera_is_not_found(self):
        r = cam("ASI 533 MC")
        self.assertNotEqual(r["level"], "found")
        self.assertEqual(r["models"], [])

    def test_ares_m_pro_with_efw(self):
        r = cam("Ares-M Pro + EFW")
        self.assertEqual(r["level"], "found")
        self.assertIn("Player One Ares-M", r["models"])
        self.assertGreaterEqual(r["score"], 17)

    def test_ares_color_not_matched(self):
        self.assertEqual(cam("Player One Ares-C Pro")["models"], [])

    def test_qhy533m_pro(self):
        r = cam("QHY533M-Pro")
        self.assertEqual(r["level"], "found")
        self.assertIn("QHY533M", r["models"])

    def test_qhy533mc_excluded(self):
        self.assertNotEqual(cam("QHY533MC")["level"], "found")

    def test_imx533_mono_is_check(self):
        r = cam("камера на imx533 моно")
        self.assertEqual(r["level"], "check")
        self.assertEqual(r["models"], [])

    def test_suffixless_is_check(self):
        self.assertEqual(cam("Продам ASI533")["level"], "check")

    def test_atr533m_and_hypercam(self):
        self.assertEqual(cam("ToupTek ATR533M")["level"], "found")
        self.assertEqual(cam("Altair Hypercam 533M Pro")["level"], "found")

    def test_cyrillic_brand_alias(self):
        self.assertEqual(cam("Продам зво асай 533мм")["level"], "found")

    def test_omegon(self):
        self.assertEqual(cam("Omegon veTEC 533M cooled")["level"], "found")

    def test_mono_and_color_is_ambiguous(self):
        r = cam("Меняю ASI533MC на ASI533MM")
        self.assertEqual(r["level"], "found")
        self.assertTrue(r["ambiguous"])

    def test_other_models_not_matched(self):
        for t in ("ASI2600MM Pro", "ASI294MC", "ASI183MM", "Колесо фильтров ZWO"):
            self.assertEqual(cam(t)["level"], "plain", t)

    def test_not_533_numbers(self):
        self.assertEqual(cam("Телескоп 5330 мм, код 15333")["level"], "plain")

    def test_bonuses_only_with_match(self):
        self.assertEqual(cam("Комплект Pro, колесо фильтров")["level"], "plain")


class WheelTests(unittest.TestCase):
    def test_zwo_efw_8x31(self):
        r = wheel("ZWO EFW 8x31")
        self.assertEqual(r["level"], "found")
        self.assertIn("ZWO EFW", r["models"])

    def test_zwo_efw_8x125_and_7x36(self):
        self.assertEqual(wheel("EFW 8x1.25 (31 мм)")["level"], "found")
        self.assertEqual(wheel("ZWO EFW 7x36")["level"], "found")

    def test_mini_5_positions_is_cut_off(self):
        self.assertEqual(wheel("EFW 5x1.25 mini")["level"], "plain")

    def test_generic_efw_is_check(self):
        self.assertEqual(wheel("Продам EFW ZWO")["level"], "check")

    def test_qhy_cfw3_m_us(self):
        r = wheel("CFW3-M-US")
        self.assertEqual(r["level"], "found")
        self.assertIn("QHY CFW3", r["models"])

    def test_qhy_five_and_six_position_variants_excluded(self):
        for t in ("QHYCFW3M-US5", "QHY CFW3S-US6", "QHYCFW3M-SR5", "QHY CFW3M-SR"):
            self.assertEqual(wheel(t)["level"], "plain", t)

    def test_qhy_cfw3m_us7(self):
        self.assertEqual(wheel("QHYCFW3M-US7")["level"], "found")

    def test_player_one_phoenix_and_toupтек(self):
        self.assertEqual(wheel("Player One Phoenix Wheel 7x36")["level"], "found")
        self.assertEqual(wheel("ToupTek AFW-M 7x36")["level"], "found")
        self.assertEqual(wheel("плеер ван колесо фильтров")["level"], "found")

    def test_manual_wheel_excluded(self):
        self.assertEqual(wheel("ZWO EFW 8x31, ручное колесо")["level"], "plain")
        self.assertEqual(wheel("Механическое колесо фильтров QHY CFW2")["level"], "plain")

    def test_filters_without_wheel_is_not_wheel(self):
        self.assertEqual(wheel("Фильтры Astronomik LRGB 31 мм")["level"], "plain")

    def test_filters_bonus(self):
        r = wheel("ZWO EFW 8x31 + фильтры LRGB, Ha, OIII, SII")
        self.assertGreaterEqual(r["score"], 15)

    def test_electronic_wheel_with_positions_is_check(self):
        r = wheel("Электронное колесо фильтров 8 позиций")
        self.assertEqual(r["level"], "check")


class ScopeTests(unittest.TestCase):
    def test_sharpstar_61edph_ll_with_l_letters(self):
        r = scope("Sharpstar 61 EDPH ll")  # две латинские L
        self.assertEqual(r["level"], "found")
        self.assertIn("Sharpstar 61EDPH II", r["models"])

    def test_sharpstar_cyrillic_61edph_lll(self):
        r = scope("шарпстар 61edph lll")
        self.assertEqual(r["level"], "found")
        self.assertIn("Sharpstar 61EDPH III", r["models"])

    def test_roman_and_digit_variants(self):
        for t, v in (("Sharpstar 61EDPH II", "II"), ("Sharpstar 61 EDPH Ⅱ", "II"),
                     ("sharp star 61edph 3", "III"), ("Sharpstar 61EDPH MK3", "III"),
                     ("61 ed ph iii", "III"), ("Sharpstar 61EDPH-2", "II"), ("61edph mk2", "II")):
            r = scope(t)
            self.assertEqual(r["level"], "found", t)
            self.assertIn("Sharpstar 61EDPH " + v, r["models"], t)

    def test_without_version_is_check(self):
        self.assertEqual(scope("Sharpstar 61EDPH")["level"], "check")

    def test_other_sharpstar_models_excluded(self):
        for t in ("Sharpstar 76EDPH", "Sharpstar 94 EDPH II", "Sharpstar 15028HNT", "Sharpstar 120 EDPH"):
            self.assertEqual(scope(t)["level"], "plain", t)

    def test_reducer_bonus(self):
        r = scope("Sharpstar 61EDPH II + редуктор 0.8")
        self.assertGreaterEqual(r["score"], 14)

    def test_accessory_only_low_priority(self):
        self.assertEqual(scope("Сумка для Sharpstar 61EDPH")["level"], "plain")

    def test_other_brand_61mm_is_not_sharpstar(self):
        self.assertEqual(scope("Askar 61 мм рефрактор")["level"], "plain")


class BundleTests(unittest.TestCase):
    def test_camera_plus_wheel_is_bundle(self):
        r = res("ASI533MM Pro + EFW 7x36")
        self.assertEqual(r["camera"]["level"], "found")
        self.assertEqual(r["wheel"]["level"], "found")
        self.assertTrue(r["bundle"])
        self.assertEqual(r["items"], ["camera", "wheel"])
        self.assertGreaterEqual(r["wheel"]["score"], 13)  # +3 за камеру на 533

    def test_three_items_bundle(self):
        r = res("Комплект: ASI533MM Pro, EFW 8x31 и Sharpstar 61EDPH III")
        self.assertEqual(r["items"], ["camera", "wheel", "scope"])
        self.assertTrue(r["bundle"])

    def test_single_item_not_bundle(self):
        r = res("Sharpstar 61 EDPH II")
        self.assertFalse(r["bundle"])
        self.assertEqual(r["items"], ["scope"])

    def test_wheel_gets_camera_bonus_only_with_camera(self):
        with_cam = res("ASI533MM + EFW 8x31")["wheel"]["score"]
        alone = res("EFW 8x31")["wheel"]["score"]
        self.assertEqual(with_cam - alone, 3)

    def test_rule_can_be_disabled(self):
        cfg = {"rules": {"scope": {"enabled": False}}}
        self.assertEqual(res("Sharpstar 61EDPH III", "", cfg)["scope"]["level"], "plain")


class HelpersTests(unittest.TestCase):
    def test_sold(self):
        self.assertTrue(match.is_sold("Окуляр. Продано"))
        self.assertTrue(match.is_sold("ASI533MM Pro (в резерве)"))
        self.assertFalse(match.is_sold("ASI533MM Pro"))

    def test_price_range_bonus(self):
        cfg = {"rules": {"camera": {"price_min": 30000, "price_max": 90000}}}
        r = match.analyze("ASI533MM", "Цена 60000 р", cfg)["camera"]
        self.assertEqual(r["score"], 12)
        self.assertEqual(match.analyze("ASI533MM", "без цены", cfg)["camera"]["score"], 10)

    def test_extract_price_variants(self):
        self.assertEqual(match.extract_price("Цена комплекта 100 тысяч рублей"), 100000)
        self.assertEqual(match.extract_price("3000 р"), 3000)
        self.assertIsNone(match.extract_price("договоримся"))
        self.assertEqual(match.extract_price("3.000 руб., за шт."), 3000)
        self.assertEqual(match.extract_price("по 3 тыс/шт."), 3000)
        self.assertEqual(match.extract_price("Цена 5500 рублей плюс пересыл"), 5500)
        self.assertIsNone(match.extract_price("5 выходов /1 вход 12 В 5,5*2,1 до 8 А. 12В/4А, M48-M42, 2шт."))


if __name__ == "__main__":
    unittest.main()
