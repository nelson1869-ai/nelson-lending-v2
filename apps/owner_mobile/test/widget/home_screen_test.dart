import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:owner_mobile/app/theme.dart';
import 'package:owner_mobile/core/storage/token_storage_service.dart';
import 'package:owner_mobile/features/auth/data/owner_auth_repository.dart';
import 'package:owner_mobile/features/auth/domain/auth_state.dart';
import 'package:owner_mobile/features/auth/domain/owner_profile.dart';
import 'package:owner_mobile/features/auth/presentation/auth_controller.dart';
import 'package:owner_mobile/features/home/presentation/home_screen.dart';

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

  testWidgets('HomeScreen renders authenticated profile and connection status',
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
        child: MaterialApp(
          theme: AppTheme.lightTheme,
          home: const HomeScreen(),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Lending Nelson Owner'), findsOneWidget);
    expect(find.text('test_owner'), findsOneWidget);
    expect(find.text('Role: Business Owner (Single Identity)'), findsOneWidget);
    expect(find.text('Connected & Ready'), findsOneWidget);
    expect(find.byIcon(Icons.logout), findsOneWidget);
  });
}
