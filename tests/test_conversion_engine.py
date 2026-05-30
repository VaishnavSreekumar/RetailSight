from app.services.conversion_engine import ConversionEngine


def test_calculate_funnel_success() -> None:
    """Verifies funnel calculations for visitor counts and conversion ratios."""
    sessions = [
        # Converted and engaged
        {
            "journey_path": ["zone_electronics"],
            "has_joined_billing_queue": True,
            "has_converted": True,
        },
        # Engaged, joined billing, did not purchase
        {
            "journey_path": ["zone_groceries"],
            "has_joined_billing_queue": True,
            "has_converted": False,
        },
        # Engaged, did not join billing, did not purchase
        {
            "journey_path": ["zone_electronics"],
            "has_joined_billing_queue": False,
            "has_converted": False,
        },
        # Not engaged (empty path), did not join billing, did not purchase
        {
            "journey_path": [],
            "has_joined_billing_queue": False,
            "has_converted": False,
        },
    ]

    funnel = ConversionEngine.calculate_funnel(sessions)

    assert funnel["entries"] == 4
    assert funnel["engaged_visitors"] == 3
    assert funnel["billing_queue_visitors"] == 2
    assert funnel["purchases"] == 1
    assert funnel["conversion_rate"] == 25.0


def test_calculate_funnel_empty() -> None:
    """Verifies that an empty sessions list yields zero conversion values safely."""
    funnel = ConversionEngine.calculate_funnel([])
    assert funnel["entries"] == 0
    assert funnel["conversion_rate"] == 0.0


def test_calculate_zone_effectiveness() -> None:
    """Verifies that zone-level metrics reflect visitor counts and dwell time averages."""
    sessions = [
        # Session 1: Visited electronics, converted
        {
            "journey_path": ["zone_electronics"],
            "zone_dwell_times": {"zone_electronics": 300000},
            "has_joined_billing_queue": True,
            "has_converted": True,
        },
        # Session 2: Visited electronics and apparel, did not convert
        {
            "journey_path": ["zone_electronics", "zone_apparel"],
            "zone_dwell_times": {"zone_electronics": 100000, "zone_apparel": 150000},
            "has_joined_billing_queue": False,
            "has_converted": False,
        },
    ]

    effectiveness = ConversionEngine.calculate_zone_effectiveness(sessions)

    # Validate Zone Electronics (2 visitors, total dwell 400000 -> average 200000, 1 converted -> 50%)
    elec = effectiveness["zone_electronics"]
    assert elec["visitors_count"] == 2
    assert elec["average_dwell_ms"] == 200000.0
    assert elec["billing_progression_rate"] == 50.0
    assert elec["downstream_conversion_rate"] == 50.0

    # Validate Zone Apparel (1 visitor, total dwell 150000 -> average 150000, 0 converted -> 0%)
    apparel = effectiveness["zone_apparel"]
    assert apparel["visitors_count"] == 1
    assert apparel["average_dwell_ms"] == 150000.0
    assert apparel["billing_progression_rate"] == 0.0
    assert apparel["downstream_conversion_rate"] == 0.0


def test_analyze_opportunity_loss() -> None:
    """Verifies that zones with high dwells, low conversion, and low progression are flagged."""
    sessions = [
        # Converted cohort: electronics zone (fast checkouts)
        {
            "journey_path": ["zone_electronics"],
            "zone_dwell_times": {"zone_electronics": 50000},
            "has_joined_billing_queue": True,
            "has_converted": True,
        },
        # Unconverted high-dwell cohort: apparel zone (lots of browsing, no conversions)
        {
            "journey_path": ["zone_apparel"],
            "zone_dwell_times": {"zone_apparel": 500000},
            "has_joined_billing_queue": False,
            "has_converted": False,
        },
        {
            "journey_path": ["zone_apparel"],
            "zone_dwell_times": {"zone_apparel": 300000},
            "has_joined_billing_queue": False,
            "has_converted": False,
        },
    ]

    # Overall Metrics for context:
    # total sessions = 3, purchases = 1 -> conversion_rate = 33.33%
    # total billing = 1 -> overall_billing_rate = 33.33%
    #
    # Zone metrics:
    # - zone_electronics: visitors = 1, avg dwell = 50000, billing = 100%, conversion = 100%
    # - zone_apparel: visitors = 2, avg dwell = 400000, billing = 0%, conversion = 0%
    #
    # Dwell Average threshold: (50000 + 400000) / 2 = 225000ms
    #
    # zone_apparel matches all criteria:
    # - avg dwell (400000) > threshold (225000) -> High Dwell
    # - conversion (0%) < overall conversion (33.33%) -> Low Conversion
    # - billing (0%) < overall billing (33.33%) -> Low Billing progression

    anomalous_zones = ConversionEngine.analyze_opportunity_loss(sessions)

    assert len(anomalous_zones) == 1
    flagged = anomalous_zones[0]
    assert flagged["zone"] == "zone_apparel"
    assert flagged["avg_dwell_ms"] == 400000.0
    assert flagged["conversion_rate"] == 0.0
    assert flagged["billing_progression_rate"] == 0.0
