import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:borrower_mobile/app/app.dart';
import 'package:borrower_mobile/core/storage/token_storage_service.dart';
import 'package:borrower_mobile/features/auth/domain/auth_state.dart';
import 'package:borrower_mobile/features/auth/domain/borrower_profile.dart';
import 'package:borrower_mobile/features/auth/presentation/auth_controller.dart';
import 'package:mocktail/mocktail.dart';

class MockTokenStorageService extends Mock implements TokenStorageService {}

void main() {
  late MockTokenStorageService mockStorage;

  setUp(() {
    mockStorage = MockTokenStorageService();
    when(() => mockStorage.getRefreshToken()).thenAnswer((_) async => null);
  });

  testWidgets('initial auth status shows SplashScreen', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          tokenStorageProvider.overrideWithValue(mockStorage),
        ],
        child: const BorrowerMobileApp(),
      ),
    );

    expect(find.text('Borrower Portal'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('unauthenticated status redirects to LoginScreen',
      (tester) async {
    final container = ProviderContainer(
      overrides: [
        tokenStorageProvider.overrideWithValue(mockStorage),
      ],
    );

    container.read(authControllerProvider.notifier).state =
        const AuthState.unauthenticated();

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const BorrowerMobileApp(),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Welcome to Lending Nelson'), findsOneWidget);
    expect(find.text('Sign In'), findsWidgets);
  });

  testWidgets('authenticated status redirects to HomeScreen', (tester) async {
    final container = ProviderContainer(
      overrides: [
        tokenStorageProvider.overrideWithValue(mockStorage),
      ],
    );

    const dummy = BorrowerProfile(
      borrowerId: 'b-id',
      accountId: 'a-id',
      firstName: 'Juan',
      lastName: 'Dela Cruz',
      phoneNumber: '+639171234567',
      accountStatus: 'active',
    );

    container.read(authControllerProvider.notifier).state =
        const AuthState.authenticated(dummy);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const BorrowerMobileApp(),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Welcome, Juan Dela Cruz'), findsOneWidget);
    expect(find.text('Account Information'), findsOneWidget);
  });
}
