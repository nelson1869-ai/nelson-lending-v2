import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:borrower_mobile/core/device/device_service.dart';
import 'package:borrower_mobile/core/storage/token_storage_service.dart';

class MockTokenStorageService extends Mock implements TokenStorageService {}

void main() {
  late MockTokenStorageService mockStorage;
  late DeviceService deviceService;

  setUp(() {
    mockStorage = MockTokenStorageService();
    deviceService = DeviceService(tokenStorage: mockStorage);
  });

  test(
      'getOrCreateDeviceIdentifier returns existing device identifier if present',
      () async {
    when(() => mockStorage.getDeviceIdentifier())
        .thenAnswer((_) async => '12345678-1234-1234-1234-123456789012');

    final deviceId = await deviceService.getOrCreateDeviceIdentifier();

    expect(deviceId, equals('12345678-1234-1234-1234-123456789012'));
    verify(() => mockStorage.getDeviceIdentifier()).called(1);
    verifyNever(() => mockStorage.saveDeviceIdentifier(any()));
  });

  test(
      'getOrCreateDeviceIdentifier generates and persists new UUID if not present',
      () async {
    when(() => mockStorage.getDeviceIdentifier()).thenAnswer((_) async => null);
    when(() => mockStorage.saveDeviceIdentifier(any()))
        .thenAnswer((_) async {});

    final deviceId = await deviceService.getOrCreateDeviceIdentifier();

    expect(deviceId.length, greaterThanOrEqualTo(16));
    expect(
        RegExp(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
            .hasMatch(deviceId),
        isTrue);
    verify(() => mockStorage.saveDeviceIdentifier(deviceId)).called(1);
  });
}
