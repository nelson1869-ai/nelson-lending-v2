import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:borrower_mobile/features/registration/presentation/registration_screen.dart';

void main() {
  testWidgets('RegistrationScreen renders registration form elements',
      (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: RegistrationScreen(),
        ),
      ),
    );

    expect(find.text('Create Borrower Account'), findsOneWidget);
    expect(find.text('First Name'), findsOneWidget);
    expect(find.text('Last Name'), findsOneWidget);
    expect(find.text('National ID / Government ID'), findsOneWidget);
    expect(find.text('Mobile Phone Number'), findsOneWidget);
    expect(find.text('Submit Registration'), findsOneWidget);
  });

  testWidgets(
      'RegistrationScreen shows validation errors when fields are empty',
      (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: RegistrationScreen(),
        ),
      ),
    );

    final submitFinder = find.text('Submit Registration');
    await tester.ensureVisible(submitFinder);
    await tester.tap(submitFinder);
    await tester.pump();

    expect(find.text('First name is required'), findsOneWidget);
    expect(find.text('Last name is required'), findsOneWidget);
    expect(find.text('Phone number is required'), findsOneWidget);
  });
}
