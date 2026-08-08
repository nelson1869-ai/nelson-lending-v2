import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:borrower_mobile/core/device/device_service.dart';
import 'package:borrower_mobile/core/storage/token_storage_service.dart';
import 'package:borrower_mobile/features/auth/data/borrower_auth_repository.dart';
import 'package:borrower_mobile/features/auth/domain/auth_state.dart';
import 'package:borrower_mobile/features/auth/domain/borrower_profile.dart';
import 'package:borrower_mobile/features/auth/presentation/auth_controller.dart';

class MockBorrowerAuthRepository extends Mock
    implements BorrowerAuthRepository {}

class MockTokenStorageService extends Mock implements TokenStorageService {}

class MockDeviceService extends Mock implements DeviceService {}

void main() {
  late MockBorrowerAuthRepository mockRepo;
  late MockTokenStorageService mockStorage;
  late MockDeviceService mockDeviceService;
  late AuthController controller;

  setUp(() {
    mockRepo = MockBorrowerAuthRepository();
    mockStorage = MockTokenStorageService();
    mockDeviceService = MockDeviceService();

    controller = AuthController(
      repository: mockRepo,
      tokenStorage: mockStorage,
      deviceService: mockDeviceService,
    );
  });

  const dummyProfile = BorrowerProfile(
    borrowerId: '00000000-0000-0000-0000-000000000001',
    accountId: '00000000-0000-0000-0000-000000000002',
    firstName: 'Juan',
    lastName: 'Dela Cruz',
    phoneNumber: '+639171234567',
    accountStatus: 'active',
  );

  test(
      'restoreSession transitions to unauthenticated when no stored token exists',
      () async {
    when(() => mockStorage.getRefreshToken()).thenAnswer((_) async => null);

    await controller.restoreSession();

    expect(controller.state.status, equals(AuthStatus.unauthenticated));
  });

  test('restoreSession succeeds when refresh token is valid', () async {
    final expires = DateTime.now().add(const Duration(minutes: 15));
    when(() => mockStorage.getRefreshToken())
        .thenAnswer((_) async => 'valid_refresh');
    when(() => mockDeviceService.getOrCreateDeviceIdentifier())
        .thenAnswer((_) async => 'device_123456789');
    when(() => mockRepo.refresh(
            refreshToken: 'valid_refresh',
            deviceIdentifier: 'device_123456789'))
        .thenAnswer((_) async => BorrowerTokenPair(
              accessToken: 'new_access',
              refreshToken: 'rotated_refresh',
              expiresAt: expires,
            ));
    when(() => mockStorage.setAccessToken('new_access', expires))
        .thenReturn(null);
    when(() => mockStorage.saveRefreshToken('rotated_refresh'))
        .thenAnswer((_) async {});
    when(() => mockRepo.getMe()).thenAnswer((_) async => dummyProfile);

    await controller.restoreSession();

    expect(controller.state.status, equals(AuthStatus.authenticated));
    expect(controller.state.borrower?.fullName, equals('Juan Dela Cruz'));
  });

  test('login authenticates credentials and updates state', () async {
    final expires = DateTime.now().add(const Duration(minutes: 15));
    when(() => mockDeviceService.getOrCreateDeviceIdentifier())
        .thenAnswer((_) async => 'device_123456789');
    when(() => mockRepo.login(
          phoneNumber: '+639171234567',
          pin: '123456',
          deviceIdentifier: 'device_123456789',
        )).thenAnswer((_) async => BorrowerTokenPair(
          accessToken: 'access_jwt',
          refreshToken: 'refresh_opaque',
          expiresAt: expires,
        ));
    when(() => mockStorage.setAccessToken('access_jwt', expires))
        .thenReturn(null);
    when(() => mockStorage.saveRefreshToken('refresh_opaque'))
        .thenAnswer((_) async {});
    when(() => mockRepo.getMe()).thenAnswer((_) async => dummyProfile);

    final success = await controller.login('+639171234567', '123456');

    expect(success, isTrue);
    expect(controller.state.status, equals(AuthStatus.authenticated));
    expect(controller.state.borrower?.accountStatus, equals('active'));
  });

  test('logout revokes refresh session and clears storage', () async {
    when(() => mockStorage.getRefreshToken())
        .thenAnswer((_) async => 'session_token');
    when(() => mockRepo.logout('session_token')).thenAnswer((_) async {});
    when(() => mockStorage.clearAll()).thenAnswer((_) async {});

    await controller.logout();

    expect(controller.state.status, equals(AuthStatus.unauthenticated));
    verify(() => mockStorage.clearAll()).called(1);
  });
}
