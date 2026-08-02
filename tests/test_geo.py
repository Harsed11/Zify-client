from vpn_configurator.core.geo import detect_country


def test_detect_from_emoji_flag():
    flag, country = detect_country({"ps": "🇩🇪 DE 01", "host": "h.com"})
    assert flag == "🇩🇪"
    assert country == "Германия"


def test_detect_from_city_remark():
    flag, country = detect_country({"ps": "Tokyo JP", "host": "h.com"})
    assert country == "Япония · Токио"


def test_detect_from_hostname():
    flag, country = detect_country({"ps": "", "host": "us-east.example.com"})
    assert country == "США"


def test_detect_unknown():
    flag, country = detect_country({"ps": "some node", "host": "unknowndomain.example"})
    assert flag is None
    assert country is None


def test_detect_from_iso_code_word():
    flag, country = detect_country({"ps": "Node [GB] 01", "host": "h.com"})
    assert country == "Великобритания"
