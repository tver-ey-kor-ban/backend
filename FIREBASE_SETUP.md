# Firebase Authentication Setup

## Overview
This backend supports Firebase Authentication for user management. Users can authenticate using Firebase SDK on the client side, and the backend verifies the Firebase ID token to create/issue its own JWT tokens.

## Setup Instructions

### 1. Create Firebase Project
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project" and follow the setup wizard
3. Enable Authentication in the left sidebar
4. Enable the sign-in methods you want (Email/Password, Google, etc.)

### 2. Generate Service Account Key
1. In Firebase Console, go to Project Settings (gear icon)
2. Go to "Service accounts" tab
3. Click "Generate new private key"
4. Save the JSON file securely

### 3. Configure Backend

#### Option A: Using Environment Variable (Recommended for Production)
Set the `FIREBASE_CREDENTIALS_JSON` environment variable with the contents of the JSON key file:

```bash
# Linux/Mac
export FIREBASE_CREDENTIALS_JSON='{"type":"service_account",...}'

# Windows PowerShell
$env:FIREBASE_CREDENTIALS_JSON='{"type":"service_account",...}'
```

#### Option B: Using File Path
Place the JSON file in the project root as `firebase-credentials.json` or set the path:

```bash
export FIREBASE_CREDENTIALS_PATH=/path/to/firebase-credentials.json
```

#### Option C: Using Docker Compose
Add to your `docker-compose.yml`:

```yaml
services:
  api:
    environment:
      - FIREBASE_CREDENTIALS_JSON=${FIREBASE_CREDENTIALS_JSON}
    volumes:
      - ./firebase-credentials.json:/code/firebase-credentials.json:ro
```

### 4. Update .env File
Add to your `.env` file:

```env
# Firebase Configuration
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
# OR
# FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}
```

## API Endpoints

### Firebase Login
```http
POST /api/v1/auth/firebase/login
Headers:
    X-Firebase-Token: <firebase_id_token>

Response:
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
}
```

### Link Account with Firebase
```http
POST /api/v1/auth/firebase/link
Headers:
    Authorization: Bearer <backend_jwt_token>
    X-Firebase-Token: <firebase_id_token>
```

### Verify Firebase Token (Debug)
```http
GET /api/v1/auth/firebase/verify-token
Headers:
    X-Firebase-Token: <firebase_id_token>
```

### Get Firebase User Info
```http
GET /api/v1/auth/firebase/me/firebase
Headers:
    Authorization: Bearer <backend_jwt_token>
```

### Set User Roles (Admin Only)
```http
POST /api/v1/auth/firebase/users/{firebase_uid}/roles
Headers:
    Authorization: Bearer <admin_jwt_token>
Body:
    ["admin", "moderator"]
```

## Flutter Integration

### 1. Add Dependencies
```yaml
dependencies:
  firebase_core: ^2.24.2
  firebase_auth: ^4.16.0
  http: ^1.1.0
```

### 2. Initialize Firebase
```dart
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_auth/firebase_auth.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  runApp(MyApp());
}
```

### 3. Login Flow
```dart
import 'package:firebase_auth/firebase_auth.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class AuthService {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  
  Future<String?> signInWithEmail(String email, String password) async {
    // Sign in with Firebase
    final credential = await _auth.signInWithEmailAndPassword(
      email: email,
      password: password,
    );
    
    // Get Firebase ID token
    final idToken = await credential.user?.getIdToken();
    
    // Send to backend
    final response = await http.post(
      Uri.parse('http://localhost:8000/api/v1/auth/firebase/login'),
      headers: {
        'X-Firebase-Token': idToken!,
      },
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['access_token']; // Backend JWT token
    }
    return null;
  }
  
  Future<String?> signInWithGoogle() async {
    // Implement Google Sign-In
    // ... get Firebase credential
    
    final idToken = await FirebaseAuth.instance.currentUser?.getIdToken();
    
    // Send to backend same as above
    // ...
  }
}
```

### 4. Making Authenticated Requests
```dart
Future<void> fetchUserData(String backendToken) async {
  final response = await http.get(
    Uri.parse('http://localhost:8000/api/v1/auth/me'),
    headers: {
      'Authorization': 'Bearer $backendToken',
    },
  );
  
  if (response.statusCode == 200) {
    final userData = jsonDecode(response.body);
    print(userData);
  }
}
```

## User Flow

1. **Client authenticates with Firebase** (Email/Password, Google, Apple, etc.)
2. **Client gets Firebase ID token** from Firebase SDK
3. **Client sends Firebase token to backend** via `X-Firebase-Token` header
4. **Backend verifies Firebase token** with Firebase Admin SDK
5. **Backend creates/updates local user** in PostgreSQL database
6. **Backend issues its own JWT token** for API access
7. **Client uses backend JWT** for subsequent API requests

## Benefits

- **Multiple auth providers**: Email, Google, Apple, Facebook, etc.
- **Email verification**: Handled by Firebase
- **Password reset**: Handled by Firebase
- **Social login**: Easy integration
- **Secure**: Firebase handles token security
- **Local user data**: Your database stores user roles and app-specific data

## Troubleshooting

### "Firebase initialization failed"
- Check that credentials file exists and is valid JSON
- Verify environment variable is set correctly
- Check Docker volume mount if using containers

### "Invalid Firebase token"
- Token may be expired (Firebase tokens expire after 1 hour)
- Refresh the token on the client side
- Ensure token is being sent in `X-Firebase-Token` header

### "User not found"
- User may exist in Firebase but not in local database
- The login endpoint should auto-create local users
- Check database connection
