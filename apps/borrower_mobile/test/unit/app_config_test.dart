import 'package:flutter_test/flutter_test.dart';
import 'package:borrower_mobile/core/config/app_config.dart';

void main() {
  test('AppConfig.fromEnvironment returns default base URL when unspecified',
      () {
    final config = AppConfig.fromEnvironment();
    expect(config.apiBaseUrl, equals('http://10.0.2.2:8000'));
  });
}
