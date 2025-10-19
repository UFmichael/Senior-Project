import { Component } from '@angular/core';
import { RouterLink, Router} from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Colorpicker } from '../colorpicker/colorpicker';

@Component({
  selector: 'app-login',
  imports: [RouterLink, FormsModule, Colorpicker],
  templateUrl: './login.html',
  styleUrl: './login.css'
})
export class Login {
  username: string = '';
  password: string = '';

  constructor(private router: Router) {}

  onLogin() {
    alert("Username: " + this.username + '\n' + "Password: " + this.password);
    this.router.navigate(['/dashboard']);
  }
}
