import 'package:flutter_test/flutter_test.dart';
import 'package:owner_mobile/core/config/app_config.dart';

void main() {
  group('AppConfig', () {
    test('default configuration provides valid values', () {
      final config = AppConfig.fromEnvironment();

      expect(config.apiBaseUrl, equals('https://lending-nelson-v2-api.onrender.com'));
      expect(config.environment, equals('production'));
    });
  });
}
