import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:owner_mobile/app/app.dart';
import 'package:owner_mobile/core/storage/token_storage_service.dart';
import 'package:owner_mobile/features/auth/data/owner_auth_repository.dart';
import 'package:owner_mobile/features/auth/domain/auth_state.dart';
import 'package:owner_mobile/features/auth/domain/owner_profile.dart';
import 'package:owner_mobile/features/auth/presentation/auth_controller.dart';

class MockOwnerAuthRepository extends Mock implements OwnerAuthRepository {}

void main() {
  late MockOwnerAuthRepository mockRepo;

  setUp(() {
    mockRepo = MockOwnerAuthRepository();
    when(() => mockRepo.checkHealth()).thenAnswer((_) async => true);
  });

  final dummyOwner = OwnerProfile(
    id: '00000000-0000-0000-0000-000000000001',
    username: 'test_owner',
    isActive: true,
    createdAt: DateTime.parse('2026-08-08T00:00:00Z'),
  );

  testWidgets('initial auth status shows SplashScreen',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authControllerProvider.overrideWith((ref) {
            final controller = AuthController(
              repository: mockRepo,
              tokenStorage: ref.watch(tokenStorageProvider),
            );
            controller.state = const AuthState.initial();
            return controller;
          }),
        ],
        child: const OwnerApp(),
      ),
    );

    await tester.pump();

    expect(find.text('Owner Mobile'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('unauthenticated status redirects to LoginScreen',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authControllerProvider.overrideWith((ref) {
            final controller = AuthController(
              repository: mockRepo,
              tokenStorage: ref.watch(tokenStorageProvider),
            );
            controller.state = const AuthState.unauthenticated();
            return controller;
          }),
        ],
        child: const OwnerApp(),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Owner Sign In'), findsOneWidget);
    expect(find.widgetWithText(ElevatedButton, 'Sign In'), findsOneWidget);
  });

  testWidgets('authenticated status redirects to HomeScreen',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authControllerProvider.overrideWith((ref) {
            final controller = AuthController(
              repository: mockRepo,
              tokenStorage: ref.watch(tokenStorageProvider),
            );
            controller.state = AuthState.authenticated(dummyOwner);
            return controller;
          }),
          ownerAuthRepositoryProvider.overrideWithValue(mockRepo),
        ],
        child: const OwnerApp(),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Lending Nelson Owner'), findsOneWidget);
    expect(find.text('test_owner'), findsOneWidget);
  });
}
