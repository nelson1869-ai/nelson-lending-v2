import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:borrower_mobile/features/auth/presentation/login_screen.dart';

void main() {
  testWidgets('LoginScreen renders login form elements', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: LoginScreen(),
        ),
      ),
    );

    expect(find.text('Welcome to Lending Nelson'), findsOneWidget);
    expect(find.text('Mobile Phone Number'), findsOneWidget);
    expect(find.text('6-Digit PIN'), findsOneWidget);
    expect(find.text('Sign In'), findsWidgets);
  });

  testWidgets('LoginScreen shows validation errors when fields are empty',
      (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: LoginScreen(),
        ),
      ),
    );

    await tester.tap(find.text('Sign In').first);
    await tester.pump();

    expect(find.text('Phone number is required'), findsOneWidget);
    expect(find.text('PIN must be 6 digits'), findsOneWidget);
  });
}
