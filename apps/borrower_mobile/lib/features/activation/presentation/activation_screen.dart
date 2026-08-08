import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/app_exception.dart';
import '../data/activation_repository.dart';

class ActivationScreen extends ConsumerStatefulWidget {
  const ActivationScreen({super.key});

  @override
  ConsumerState<ActivationScreen> createState() => _ActivationScreenState();
}

class _ActivationScreenState extends ConsumerState<ActivationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _phoneController = TextEditingController();
  final _codeController = TextEditingController();
  final _pinController = TextEditingController();
  final _confirmPinController = TextEditingController();

  bool _obscurePin = true;
  bool _isLoading = false;
  String? _errorMessage;
  bool _isSuccess = false;

  @override
  void dispose() {
    _phoneController.dispose();
    _codeController.dispose();
    _pinController.dispose();
    _confirmPinController.dispose();
    super.dispose();
  }

  Future<void> _submitActivation() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final phone = _phoneController.text.trim();
    final code = _codeController.text.trim();
    final pin = _pinController.text.trim();

    try {
      final repo = ref.read(activationRepositoryProvider);
      await repo.activate(
        phoneNumber: phone,
        activationCode: code,
        pin: pin,
      );

      // Discard sensitive PIN from text fields immediately
      _pinController.clear();
      _confirmPinController.clear();

      setState(() {
        _isLoading = false;
        _isSuccess = true;
      });
    } on UnauthorizedException catch (_) {
      _pinController.clear();
      _confirmPinController.clear();
      setState(() {
        _isLoading = false;
        _errorMessage =
            'Activation failed. Check your phone number, activation code, or PIN.';
      });
    } on AppException catch (e) {
      _pinController.clear();
      _confirmPinController.clear();
      setState(() {
        _isLoading = false;
        _errorMessage = e.message;
      });
    } catch (_) {
      _pinController.clear();
      _confirmPinController.clear();
      setState(() {
        _isLoading = false;
        _errorMessage =
            'Activation failed. Please check the details or request a new code from the lender.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Borrower Account Activation'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: _isSuccess ? _buildSuccessView() : _buildFormView(),
        ),
      ),
    );
  }

  Widget _buildFormView() {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'Activate Your Account',
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          const Text(
            'Enter the 6-digit activation code provided by the lender and set up your 6-digit PIN.',
            style: TextStyle(fontSize: 14, color: Colors.grey),
          ),
          const SizedBox(height: 24),
          if (_errorMessage != null) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.errorContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                _errorMessage!,
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onErrorContainer,
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],
          TextFormField(
            controller: _phoneController,
            keyboardType: TextInputType.phone,
            decoration: const InputDecoration(
              labelText: 'Mobile Phone Number',
              hintText: 'e.g. +639171234567 or 09171234567',
              prefixIcon: Icon(Icons.phone),
            ),
            validator: (v) => (v == null || v.trim().isEmpty)
                ? 'Phone number is required'
                : null,
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _codeController,
            keyboardType: TextInputType.number,
            maxLength: 6,
            decoration: const InputDecoration(
              labelText: '6-Digit Activation Code',
              hintText: '123456',
              prefixIcon: Icon(Icons.vpn_key),
              counterText: '',
            ),
            validator: (v) {
              if (v == null || v.trim().isEmpty)
                return 'Activation code is required';
              if (!RegExp(r'^\d{6}$').hasMatch(v.trim())) {
                return 'Code must be exactly 6 digits';
              }
              return null;
            },
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _pinController,
            keyboardType: TextInputType.number,
            obscureText: _obscurePin,
            maxLength: 6,
            decoration: InputDecoration(
              labelText: 'Create 6-Digit PIN',
              prefixIcon: const Icon(Icons.lock),
              counterText: '',
              suffixIcon: IconButton(
                icon: Icon(
                  _obscurePin ? Icons.visibility_off : Icons.visibility,
                ),
                onPressed: () => setState(() => _obscurePin = !_obscurePin),
              ),
            ),
            validator: (v) {
              if (v == null || v.trim().isEmpty) return 'PIN is required';
              if (!RegExp(r'^\d{6}$').hasMatch(v.trim())) {
                return 'PIN must be exactly 6 digits';
              }
              return null;
            },
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _confirmPinController,
            keyboardType: TextInputType.number,
            obscureText: _obscurePin,
            maxLength: 6,
            decoration: const InputDecoration(
              labelText: 'Confirm 6-Digit PIN',
              prefixIcon: Icon(Icons.lock_outline),
              counterText: '',
            ),
            validator: (v) {
              if (v == null || v.trim().isEmpty)
                return 'Please confirm your PIN';
              if (v.trim() != _pinController.text.trim()) {
                return 'PINs do not match';
              }
              return null;
            },
          ),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _isLoading ? null : _submitActivation,
            child: _isLoading
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Activate Account'),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text('Already activated? '),
              TextButton(
                onPressed: () => context.go('/login'),
                child: const Text('Sign In'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSuccessView() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 32),
        const Icon(Icons.verified_user, size: 80, color: Colors.green),
        const SizedBox(height: 16),
        const Text(
          'Account Activated!',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 16),
        const Card(
          child: Padding(
            padding: EdgeInsets.all(16.0),
            child: Text(
              'Your borrower account has been successfully activated. You can now sign in using your mobile phone number and 6-digit PIN.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 15),
            ),
          ),
        ),
        const SizedBox(height: 32),
        ElevatedButton(
          onPressed: () => context.go('/login'),
          child: const Text('Proceed to Sign In'),
        ),
      ],
    );
  }
}
