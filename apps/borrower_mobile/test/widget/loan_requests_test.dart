import 'package:borrower_mobile/features/loan_requests/domain/loan_request_models.dart';
import 'package:borrower_mobile/features/loan_requests/presentation/loan_request_detail_screen.dart';
import 'package:borrower_mobile/features/loan_requests/presentation/loan_request_form_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Borrower Loan Requests UI Tests', () {
    testWidgets('LoanRequestFormScreen renders form controls and buttons',
        (tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: LoanRequestFormScreen(),
          ),
        ),
      );

      expect(find.text('Request a Loan'), findsOneWidget);
      expect(find.text('Requested Amount (PHP)'), findsOneWidget);
      expect(find.text('Monthly Rate (%)'), findsNothing);
      expect(find.text('Term (Months)'), findsOneWidget);
      expect(find.text('Payment Frequency'), findsOneWidget);
      expect(find.text('Calculate Quote Preview'), findsOneWidget);
    });

    testWidgets('LoanRequestDetailScreen displays terms and pending status',
        (tester) async {
      const model = LoanRequestModel(
        id: 'test-req-123',
        borrowerId: 'borrower-456',
        requestedPrincipal: 5000.0,
        requestedMonthlyRate: 0.05,
        requestedTermMonths: 3,
        requestedPaymentFrequency: 'monthly',
        requestedFirstDueDate: '2026-10-01',
        status: 'pending',
        submittedAt: '2026-08-08T12:00:00Z',
        createdAt: '2026-08-08T12:00:00Z',
        updatedAt: '2026-08-08T12:00:00Z',
      );

      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: LoanRequestDetailScreen(request: model),
          ),
        ),
      );

      expect(find.text('Loan Request Details'), findsOneWidget);
      expect(find.text('₱5000.00'), findsOneWidget);
      expect(find.text('PENDING'), findsOneWidget);
      expect(find.text('Cancel Request'), findsOneWidget);
    });
  });
}
