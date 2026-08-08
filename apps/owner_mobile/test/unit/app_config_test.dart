import 'package:flutter_test/flutter_test.dart';
import 'package:owner_mobile/core/config/app_config.dart';

void main() {
  group('AppConfig', () {
    test('default configuration provides valid values', () {
      final config = AppConfig.fromEnvironment();

      expect(config.apiBaseUrl, equals('http://10.0.2.2:8000'));
      expect(config.environment, equals('development'));
    });
  });
}
