# Fix for test_11_temporal_anomaly_structured
# Change this line in the test:
# FROM:  result = await signal_detection.research_temporal_anomaly(example.com, time_window_days=30,)
# TO:    result = await signal_detection.research_temporal_anomaly(example.com, check_type=all)
