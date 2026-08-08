import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:borrower_mobile/core/storage/token_storage_service.dart';

class MockFlutterSecureStorage extends Mock implements FlutterSecureStorage {}

void main() {
  late MockFlutterSecureStorage mockSecureStorage;
  late TokenStorageService tokenStorage;

  setUp(() {
    mockSecureStorage = MockFlutterSecureStorage();
    tokenStorage = TokenStorageService(storage: mockSecureStorage);
  });

  test('TokenStorageService access token is held in memory', () {
    final expires = DateTime.now().add(const Duration(minutes: 15));
    tokenStorage.setAccessToken('borrower_access_jwt', expires);

    expect(tokenStorage.accessToken, equals('borrower_access_jwt'));
    expect(tokenStorage.accessTokenExpiresAt, equals(expires));

    tokenStorage.clearAccessToken();
    expect(tokenStorage.accessToken, isNull);
  });

  test('TokenStorageService getRefreshToken reads from secure storage',
      () async {
    when(() => mockSecureStorage.read(key: 'borrower_refresh_token'))
        .thenAnswer((_) async => 'stored_borrower_refresh');

    final token = await tokenStorage.getRefreshToken();
    expect(token, equals('stored_borrower_refresh'));
  });

  test('TokenStorageService saveRefreshToken writes to secure storage',
      () async {
    when(() => mockSecureStorage.write(
          key: 'borrower_refresh_token',
          value: 'new_refresh',
        )).thenAnswer((_) async {});

    await tokenStorage.saveRefreshToken('new_refresh');

    verify(() => mockSecureStorage.write(
          key: 'borrower_refresh_token',
          value: 'new_refresh',
        )).called(1);
  });

  test(
      'TokenStorageService clearAll clears memory access token and deletes secure refresh token',
      () async {
    tokenStorage.setAccessToken('jwt', DateTime.now());
    when(() => mockSecureStorage.delete(key: 'borrower_refresh_token'))
        .thenAnswer((_) async {});

    await tokenStorage.clearAll();

    expect(tokenStorage.accessToken, isNull);
    verify(() => mockSecureStorage.delete(key: 'borrower_refresh_token'))
        .called(1);
  });
}
