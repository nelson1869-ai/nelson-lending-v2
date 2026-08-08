import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:borrower_mobile/core/config/app_config.dart';
import 'package:borrower_mobile/core/device/device_service.dart';
import 'package:borrower_mobile/core/network/api_client.dart';
import 'package:borrower_mobile/core/storage/token_storage_service.dart';
import 'package:borrower_mobile/features/auth/domain/auth_state.dart';
import 'package:borrower_mobile/features/auth/domain/borrower_profile.dart';
import 'package:borrower_mobile/features/auth/presentation/auth_controller.dart';
import 'package:borrower_mobile/features/home/presentation/home_screen.dart';
import 'package:mocktail/mocktail.dart';

class MockTokenStorageService extends Mock implements TokenStorageService {}

class MockDio extends Mock implements Dio {}

void main() {
  late MockTokenStorageService mockStorage;
  late MockDio mockDio;

  setUp(() {
    mockStorage = MockTokenStorageService();
    mockDio = MockDio();

    when(() => mockDio.interceptors).thenReturn(Interceptors());
    when(() => mockDio.get('/health/ready')).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/health/ready'),
        statusCode: 200,
      ),
    );
  });

  testWidgets('HomeScreen renders authenticated profile and connection status',
      (tester) async {
    const profile = BorrowerProfile(
      borrowerId: 'b-1234',
      accountId: 'a-5678',
      firstName: 'Juan',
      lastName: 'Dela Cruz',
      phoneNumber: '+639171234567',
      accountStatus: 'active',
    );

    final mockApiClient = ApiClient(
      config: const AppConfig(apiBaseUrl: 'http://localhost'),
      tokenStorage: mockStorage,
      deviceService: DeviceService(tokenStorage: mockStorage),
      customDio: mockDio,
    );

    final container = ProviderContainer(
      overrides: [
        tokenStorageProvider.overrideWithValue(mockStorage),
        apiClientProvider.overrideWithValue(mockApiClient),
      ],
    );

    container.read(authControllerProvider.notifier).state =
        const AuthState.authenticated(profile);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(
          home: HomeScreen(),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Welcome, Juan Dela Cruz'), findsOneWidget);
    expect(find.text('+639171234567'), findsOneWidget);
    expect(find.text('Account Information'), findsOneWidget);
    expect(find.text('System Connection'), findsOneWidget);
  });
}
