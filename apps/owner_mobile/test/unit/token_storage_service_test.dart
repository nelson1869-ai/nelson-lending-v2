import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:owner_mobile/core/storage/token_storage_service.dart';

class MockFlutterSecureStorage extends Mock implements FlutterSecureStorage {}

void main() {
  late MockFlutterSecureStorage mockStorage;
  late TokenStorageService service;

  setUp(() {
    mockStorage = MockFlutterSecureStorage();
    service = TokenStorageService(storage: mockStorage);
  });

  group('TokenStorageService', () {
    test('access token is held in memory', () {
      expect(service.accessToken, isNull);
      expect(service.hasValidAccessToken, isFalse);

      final futureDate = DateTime.now().add(const Duration(hours: 1));
      service.setAccessToken('test_jwt_access_token', futureDate);

      expect(service.accessToken, equals('test_jwt_access_token'));
      expect(service.hasValidAccessToken, isTrue);

      service.clearAccessToken();
      expect(service.accessToken, isNull);
    });

    test('getRefreshToken reads from secure storage', () async {
      when(() => mockStorage.read(key: 'owner_refresh_token'))
          .thenAnswer((_) async => 'stored_refresh_token');

      final result = await service.getRefreshToken();
      expect(result, equals('stored_refresh_token'));
    });

    test('saveRefreshToken writes to secure storage', () async {
      when(() =>
              mockStorage.write(key: 'owner_refresh_token', value: 'new_token'))
          .thenAnswer((_) async {});

      await service.saveRefreshToken('new_token');

      verify(() =>
              mockStorage.write(key: 'owner_refresh_token', value: 'new_token'))
          .called(1);
    });

    test('clearAll clears memory access token and deletes secure refresh token',
        () async {
      service.setAccessToken(
          'acc', DateTime.now().add(const Duration(minutes: 5)));
      when(() => mockStorage.delete(key: 'owner_refresh_token'))
          .thenAnswer((_) async {});

      await service.clearAll();

      expect(service.accessToken, isNull);
      verify(() => mockStorage.delete(key: 'owner_refresh_token')).called(1);
    });
  });
}
