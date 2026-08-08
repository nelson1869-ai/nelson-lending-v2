import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/loan_request_models.dart';
import 'loan_requests_controller.dart';

class LoanRequestFormScreen extends ConsumerStatefulWidget {
  const LoanRequestFormScreen({super.key});

  @override
  ConsumerState<LoanRequestFormScreen> createState() =>
      _LoanRequestFormScreenState();
}

class _LoanRequestFormScreenState
    extends ConsumerState<LoanRequestFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _principalController = TextEditingController(text: '5000');
  final _rateController = TextEditingController(text: '5.0');
  final _termController = TextEditingController(text: '3');

  String _paymentFrequency = 'monthly';
  DateTime _firstDueDate = DateTime.now().add(const Duration(days: 30));

  @override
  void dispose() {
    _principalController.dispose();
    _rateController.dispose();
    _termController.dispose();
    super.dispose();
  }

  String _formatDate(DateTime dt) {
    return '${dt.year.toString().padLeft(4, '0')}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')}';
  }

  void _calculateQuote() {
    if (!_formKey.currentState!.validate()) return;

    final principal = double.parse(_principalController.text.trim());
    final ratePercent = double.parse(_rateController.text.trim());
    final monthlyRate = ratePercent / 100.0;
    final termMonths = int.parse(_termController.text.trim());

    ref.read(loanRequestsControllerProvider.notifier).calculateQuote(
          principal: principal,
          monthlyRate: monthlyRate,
          termMonths: termMonths,
          paymentFrequency: _paymentFrequency,
          firstDueDate: _formatDate(_firstDueDate),
        );
  }

  Future<void> _submitRequest() async {
    if (!_formKey.currentState!.validate()) return;

    final principal = double.parse(_principalController.text.trim());
    final ratePercent = double.parse(_rateController.text.trim());
    final monthlyRate = ratePercent / 100.0;
    final termMonths = int.parse(_termController.text.trim());

    final success = await ref
        .read(loanRequestsControllerProvider.notifier)
        .submitRequest(
          principal: principal,
          monthlyRate: monthlyRate,
          termMonths: termMonths,
          paymentFrequency: _paymentFrequency,
          firstDueDate: _formatDate(_firstDueDate),
        );

    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Loan request submitted successfully!')),
      );
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(loanRequestsControllerProvider);
    final quote = state.currentQuote;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Request a Loan'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (state.errorMessage != null) ...[
                Card(
                  color: Colors.red.shade50,
                  child: Padding(
                    padding: const EdgeInsets.all(12.0),
                    child: Text(
                      state.errorMessage!,
                      style: TextStyle(color: Colors.red.shade900),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
              ],
              TextFormField(
                controller: _principalController,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                  labelText: 'Requested Amount (PHP)',
                  prefixText: '₱ ',
                  border: OutlineInputBorder(),
                ),
                validator: (val) {
                  if (val == null || val.trim().isEmpty) return 'Required';
                  final n = double.tryParse(val.trim());
                  if (n == null || n <= 0) return 'Must be positive number';
                  return null;
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _rateController,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                  labelText: 'Monthly Rate (%)',
                  suffixText: '%',
                  border: OutlineInputBorder(),
                ),
                validator: (val) {
                  if (val == null || val.trim().isEmpty) return 'Required';
                  final n = double.tryParse(val.trim());
                  if (n == null || n < 0) return 'Must be non-negative';
                  return null;
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _termController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Term (Months)',
                  suffixText: 'months',
                  border: OutlineInputBorder(),
                ),
                validator: (val) {
                  if (val == null || val.trim().isEmpty) return 'Required';
                  final n = int.tryParse(val.trim());
                  if (n == null || n <= 0) return 'Must be positive integer';
                  return null;
                },
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                initialValue: _paymentFrequency,
                decoration: const InputDecoration(
                  labelText: 'Payment Frequency',
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(
                    value: 'monthly',
                    child: Text('Monthly'),
                  ),
                  DropdownMenuItem(
                    value: 'twice_monthly',
                    child: Text('Twice a Month (15th / Month-End)'),
                  ),
                ],
                onChanged: (val) {
                  if (val != null) {
                    setState(() {
                      _paymentFrequency = val;
                      if (_paymentFrequency == 'twice_monthly') {
                        _firstDueDate = DateTime(_firstDueDate.year,
                            _firstDueDate.month, 15);
                      }
                    });
                  }
                },
              ),
              const SizedBox(height: 16),
              InkWell(
                onTap: () async {
                  final picked = await showDatePicker(
                    context: context,
                    initialDate: _firstDueDate,
                    firstDate: DateTime.now(),
                    lastDate: DateTime.now().add(const Duration(days: 365)),
                  );
                  if (picked != null) {
                    setState(() {
                      _firstDueDate = picked;
                    });
                  }
                },
                child: InputDecorator(
                  decoration: const InputDecoration(
                    labelText: 'First Due Date',
                    border: OutlineInputBorder(),
                    suffixIcon: Icon(Icons.calendar_today),
                  ),
                  child: Text(_formatDate(_firstDueDate)),
                ),
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: state.isQuoteLoading ? null : _calculateQuote,
                icon: const Icon(Icons.calculate),
                label: Text(state.isQuoteLoading
                    ? 'Calculating Quote...'
                    : 'Calculate Quote Preview'),
              ),
              if (quote != null) ...[
                const SizedBox(height: 24),
                _buildQuotePreviewCard(quote),
                const SizedBox(height: 24),
                ElevatedButton(
                  onPressed: state.isLoading ? null : _submitRequest,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Theme.of(context).colorScheme.primary,
                    foregroundColor: Theme.of(context).colorScheme.onPrimary,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                  child: Text(
                    state.isLoading ? 'Submitting...' : 'Submit Loan Request',
                    style: const TextStyle(
                        fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildQuotePreviewCard(LoanQuoteModel quote) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Quote Preview (Reducing Balance)',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
            const Divider(height: 20),
            _buildRow('Periodic Payment',
                '₱${quote.periodicPayment.toStringAsFixed(2)}'),
            _buildRow('Total Payments', '${quote.numberOfPayments} payments'),
            _buildRow(
                'Total Interest', '₱${quote.totalInterest.toStringAsFixed(2)}'),
            _buildRow(
                'Total Repayable', '₱${quote.totalAmount.toStringAsFixed(2)}'),
            const SizedBox(height: 12),
            const Text(
              'Schedule Projection',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            ...quote.schedule.map((item) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4.0),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('#${item.paymentNumber} (${item.dueDate})'),
                      Text(
                        '₱${item.paymentAmount.toStringAsFixed(2)} (Int: ₱${item.interestPaid.toStringAsFixed(2)})',
                        style: const TextStyle(fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
                )),
          ],
        ),
      ),
    );
  }

  Widget _buildRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}
